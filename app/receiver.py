"""UDP receiver: sequence tracking, ACK/NACK, duplicate suppression and telemetry."""
import argparse
import socket
import time
from collections import defaultdict
from app.protocol import DATA, ACK, NACK, TELEMETRY, encode_message, decode_message


class UDPReceiver:
    def __init__(self, host, port, sender_ip, sender_port, grace, telemetry_host,
                 telemetry_port, telemetry_interval, stream_id):
        self.host, self.port = host, port
        self.sender_ip, self.sender_port = sender_ip, sender_port
        self.grace = grace
        self.telemetry_target = (telemetry_host, telemetry_port) if telemetry_host else None
        self.telemetry_interval = telemetry_interval
        self.stream_id = stream_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.settimeout(0.1)
        self.states = defaultdict(lambda: {"received": set(), "highest": 0, "missing": {},
                                           "unique": 0, "duplicates": 0, "missing_detected": 0,
                                           "recovered": 0, "window_expected": 0, "window_received": 0, "window_missing": 0})
        self.report_id = 0
        self.last_telemetry = time.monotonic()
        self.last_stats = time.monotonic()
        print(f"[RECEIVER] Listening on {host}:{port}; expected sender={sender_ip}:{sender_port}")
        if self.telemetry_target:
            print(f"[RECEIVER] Telemetry target={self.telemetry_target[0]}:{self.telemetry_target[1]}")

    def feedback(self, kind, stream_id, seq, address):
        self.sock.sendto(encode_message(kind, stream_id, seq), address)
        print(f"[RECEIVER] {kind} seq={seq} -> {address[0]}:{address[1]}")

    def handle_data(self, msg, address):
        if address[0] != self.sender_ip or (self.sender_port and address[1] != self.sender_port):
            print(f"[RECEIVER] Rejected unexpected DATA source {address}")
            return
        stream = msg["stream_id"]
        if stream != self.stream_id:
            print(f"[RECEIVER] Rejected unexpected stream {stream}")
            return
        seq = msg["seq"]
        st = self.states[stream]
        if seq in st["received"]:
            st["duplicates"] += 1
            print(f"[RECEIVER] Duplicate seq={seq}; not delivered again")
            self.feedback(ACK, stream, seq, address)
            return

        if seq > st["highest"]:
            delta = seq - st["highest"]
            st["window_expected"] += delta
            st["window_received"] += 1
            for missing_seq in range(st["highest"] + 1, seq):
                if missing_seq not in st["received"] and missing_seq not in st["missing"]:
                    st["missing"][missing_seq] = {"detected": time.monotonic(), "nack_sent": False}
                    st["missing_detected"] += 1
                    print(f"[RECEIVER] Gap detected: seq={missing_seq} (grace {self.grace}s)")
            st["highest"] = seq
        else:
            info = st["missing"].pop(seq, None)
            if info:
                st["recovered"] += 1
                print(f"[RECEIVER] Late/retransmitted seq={seq} recovered (NACK sent={info['nack_sent']})")

        st["received"].add(seq)
        st["unique"] += 1
        print(f"[RECEIVER] DELIVER seq={seq}: {msg['payload']}")
        self.feedback(ACK, stream, seq, address)

    def check_gaps(self, address):
        now = time.monotonic()
        for stream, st in self.states.items():
            for seq, info in list(st["missing"].items()):
                if not info["nack_sent"] and now - info["detected"] >= self.grace:
                    self.feedback(NACK, stream, seq, address)
                    info["nack_sent"] = True
                    st["window_missing"] += 1

    def send_telemetry(self):
        if not self.telemetry_target:
            return
        now = time.monotonic()
        if now - self.last_telemetry < self.telemetry_interval:
            return
        self.last_telemetry = now
        st = self.states[self.stream_id]
        expected = st["window_expected"]
        missing = st["window_missing"]
        # Wait until the reordering grace has expired for all observed gaps;
        # this prevents transient reordering from being reported as loss.
        if any(not item["nack_sent"] for item in st["missing"].values()):
            return
        if expected <= 0:
            return
        # Count only gaps that survived the reordering grace period.
        received = max(0, expected - missing)
        loss = max(0.0, missing * 100.0 / expected)
        self.report_id += 1
        extra = {"report_id": self.report_id, "window_expected": expected,
                 "window_received": received, "loss_pct": round(loss, 3),
                 "last_received_seq": st["highest"]}
        packet = encode_message(TELEMETRY, self.stream_id, extra=extra)
        try:
            self.sock.sendto(packet, self.telemetry_target)
            print(f"[RECEIVER] TELEMETRY report={self.report_id} expected={expected} received={received} loss={loss:.1f}%")
        except OSError as exc:
            print(f"[RECEIVER] Telemetry send failed: {exc}")
        st["window_expected"] = 0
        st["window_received"] = 0
        st["window_missing"] = 0

    def print_stats(self):
        print("\n========== RECEIVER STATISTICS ==========")
        for stream, st in self.states.items():
            unrecovered = len(st["missing"])
            print(f"stream={stream} unique={st['unique']} duplicates={st['duplicates']} "
                  f"missing_detected={st['missing_detected']} recovered={st['recovered']} "
                  f"currently_missing={unrecovered}")
        print("=========================================\n")

    def run(self):
        try:
            while True:
                address = None
                try:
                    data, address = self.sock.recvfrom(65535)
                    msg = decode_message(data)
                    if msg["type"] == DATA:
                        self.handle_data(msg, address)
                except socket.timeout:
                    pass
                except ValueError as exc:
                    print(f"[RECEIVER] Invalid packet: {exc}")
                if address:
                    self.check_gaps(address)
                else:
                    # NACKs are sent to the most recently seen sender.
                    if hasattr(self, "last_sender") and self.last_sender:
                        self.check_gaps(self.last_sender)
                if address:
                    self.last_sender = address
                self.send_telemetry()
                if time.monotonic() - self.last_stats >= 5:
                    self.print_stats()
                    self.last_stats = time.monotonic()
        except KeyboardInterrupt:
            print("\n[RECEIVER] Shutting down")
            self.print_stats()
        finally:
            self.sock.close()


def main():
    p = argparse.ArgumentParser(description="Team 11 UDP receiver")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--sender-ip", default="127.0.0.1")
    p.add_argument("--sender-port", type=int, default=5000)
    p.add_argument("--grace", type=float, default=0.35)
    p.add_argument("--telemetry-host", default="")
    p.add_argument("--telemetry-port", type=int, default=6000)
    p.add_argument("--telemetry-interval", type=float, default=1.0)
    p.add_argument("--stream-id", default="team11")
    a = p.parse_args()
    UDPReceiver(a.host, a.port, a.sender_ip, a.sender_port, a.grace,
                a.telemetry_host, a.telemetry_port, a.telemetry_interval, a.stream_id).run()

if __name__ == "__main__":
    main()
