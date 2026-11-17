"""UDP sender with an ACK-tracked buffer and bounded NACK/timeout retransmission."""
import argparse
import socket
import time
from app.protocol import DATA, ACK, NACK, encode_message, decode_message


class UDPSender:
    def __init__(self, bind_host, bind_port, receiver_host, receiver_port,
                 timeout, retries, interval, stream_id):
        self.receiver = (receiver_host, receiver_port)
        self.timeout, self.max_retries, self.interval = timeout, retries, interval
        self.stream_id = stream_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((bind_host, bind_port))
        self.sock.setblocking(False)
        self.pending = {}
        self.stats = {"original": 0, "wire_data": 0, "acknowledged": 0,
                      "retransmissions": 0, "unrecovered": 0}

    def send_packet(self, seq, payload, retransmission=False):
        packet = encode_message(DATA, self.stream_id, seq, payload)
        self.sock.sendto(packet, self.receiver)
        self.stats["wire_data"] += 1
        if retransmission:
            self.stats["retransmissions"] += 1
            print(f"[SENDER] RETRANSMIT seq={seq}")
        else:
            self.stats["original"] += 1
            print(f"[SENDER] SEND seq={seq}: {payload}")

    def read_feedback(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)
            except BlockingIOError:
                return
            if addr[0] != self.receiver[0] or addr[1] != self.receiver[1]:
                print(f"[SENDER] Ignored feedback from {addr}")
                continue
            try:
                msg = decode_message(data)
            except ValueError as exc:
                print(f"[SENDER] Invalid feedback: {exc}")
                continue
            if msg.get("stream_id") != self.stream_id or msg.get("type") not in {ACK, NACK}:
                continue
            seq = msg["seq"]
            item = self.pending.get(seq)
            if not item:
                continue
            if msg["type"] == ACK:
                del self.pending[seq]
                self.stats["acknowledged"] += 1
                print(f"[SENDER] ACK seq={seq}")
            else:
                item["nack"] = True
                print(f"[SENDER] NACK seq={seq}")

    def retry_due_packets(self, now):
        for seq, item in list(self.pending.items()):
            if not item["nack"] and now - item["last_sent"] < self.timeout:
                continue
            if item["retries"] >= self.max_retries:
                print(f"[SENDER] RETRY LIMIT seq={seq}; unrecovered")
                del self.pending[seq]
                self.stats["unrecovered"] += 1
                continue
            self.send_packet(seq, item["payload"], retransmission=True)
            item["last_sent"] = now
            item["retries"] += 1
            item["nack"] = False

    def send_stream(self, count):
        print(f"[SENDER] Starting stream: count={count}, receiver={self.receiver}")
        for seq in range(1, count + 1):
            payload = f"Team 11 Packet {seq}"
            self.pending[seq] = {"payload": payload, "last_sent": time.monotonic(),
                                 "retries": 0, "nack": False}
            self.send_packet(seq, payload)
            end = time.monotonic() + self.interval
            while time.monotonic() < end:
                self.read_feedback()
                self.retry_due_packets(time.monotonic())
                time.sleep(0.005)

        print("[SENDER] Waiting for outstanding ACKs/retries...")
        deadline = time.monotonic() + self.timeout * (self.max_retries + 2) + 2
        while self.pending and time.monotonic() < deadline:
            self.read_feedback()
            self.retry_due_packets(time.monotonic())
            time.sleep(0.01)
        for seq in list(self.pending):
            print(f"[SENDER] Receiver unavailable or no ACK for seq={seq}")
            self.stats["unrecovered"] += 1
            del self.pending[seq]
        self.print_stats()

    def print_stats(self):
        original = self.stats["original"]
        overhead = (self.stats["retransmissions"] / original * 100) if original else 0
        print("\n========== SENDER STATISTICS ==========")
        print(f"Original DATA       : {original}")
        print(f"Wire DATA total     : {self.stats['wire_data']}")
        print(f"ACKs received       : {self.stats['acknowledged']}")
        print(f"Retransmissions     : {self.stats['retransmissions']}")
        print(f"Unrecovered packets : {self.stats['unrecovered']}")
        print(f"Retransmission overhead: {overhead:.2f}%")
        print("======================================\n")

    def close(self):
        self.sock.close()


def main():
    p = argparse.ArgumentParser(description="Team 11 UDP sender")
    p.add_argument("--bind-host", default="127.0.0.1")
    p.add_argument("--bind-port", type=int, default=5000)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--count", type=int, default=30)
    p.add_argument("--timeout", type=float, default=0.8)
    p.add_argument("--retries", type=int, default=4)
    p.add_argument("--interval", type=float, default=0.05)
    p.add_argument("--stream-id", default="team11")
    a = p.parse_args()
    if a.count < 1 or a.timeout <= 0 or a.retries < 0 or a.interval < 0:
        p.error("count must be positive; timeout positive; retries/interval non-negative")
    sender = UDPSender(a.bind_host, a.bind_port, a.host, a.port,
                       a.timeout, a.retries, a.interval, a.stream_id)
    try:
        sender.send_stream(a.count)
    finally:
        sender.close()

if __name__ == "__main__":
    main()
