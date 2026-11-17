
import socket
import time
import argparse

from app.protocol import (
    DATA,
    ACK,
    NACK,
    encode_message,
    decode_message
)


class UDPSender:
    def __init__(self, receiver_host="127.0.0.1",
                 receiver_port=5001, timeout=1.0,
                 max_retries=5, interval=0.2):

        self.receiver = (receiver_host, receiver_port)
        self.timeout = timeout
        self.max_retries = max_retries
        self.interval = interval

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.settimeout(0.1)

        self.stream_id = "team11"
        self.next_seq = 1
        self.pending = {}

        self.stats = {
            "sent": 0,
            "acknowledged": 0,
            "retransmissions": 0,
            "failed": 0
        }

    def send_packet(self, seq, payload, retransmission=False):

        packet = encode_message(
            DATA,
            self.stream_id,
            seq,
            payload
        )

        self.socket.sendto(packet, self.receiver)

        self.stats["sent"] += 1

        if retransmission:
            self.stats["retransmissions"] += 1
            print(f"[SENDER] Retransmitted seq={seq}")
        else:
            print(f"[SENDER] Sent seq={seq}: {payload}")

    def handle_feedback(self, message):

        message_type = message["type"]
        seq = message["seq"]

        if seq not in self.pending:
            return

        if message_type == ACK:
            del self.pending[seq]
            self.stats["acknowledged"] += 1
            print(f"[SENDER] ACK received for seq={seq}")

        elif message_type == NACK:
            self.pending[seq]["nack_received"] = True
            print(f"[SENDER] NACK received for seq={seq}")

    def process_feedback(self):

        try:
            data, address = self.socket.recvfrom(65535)

            if address[0] != self.receiver[0]:
                return

            message = decode_message(data)

            if message["stream_id"] != self.stream_id:
                return

            if message["type"] in {ACK, NACK}:
                self.handle_feedback(message)

        except socket.timeout:
            pass

        except ValueError as error:
            print(f"[SENDER] Invalid feedback: {error}")

    def check_retransmissions(self):

        now = time.time()

        for seq in list(self.pending):

            packet_info = self.pending[seq]

            if packet_info["nack_received"] or now - packet_info["last_sent"] >= self.timeout:

                if packet_info["retries"] >= self.max_retries:
                    print(f"[SENDER] Retry limit reached for seq={seq}")
                    del self.pending[seq]
                    self.stats["failed"] += 1
                    continue

                self.send_packet(
                    seq,
                    packet_info["payload"],
                    retransmission=True
                )

                packet_info["last_sent"] = now
                packet_info["retries"] += 1
                packet_info["nack_received"] = False

    def send_stream(self, count=10):

        print("[SENDER] Starting UDP transmission...")

        for _ in range(count):

            seq = self.next_seq
            self.next_seq += 1

            payload = f"Team 11 Packet {seq}"

            self.pending[seq] = {
                "payload": payload,
                "last_sent": time.time(),
                "retries": 0,
                "nack_received": False
            }

            self.send_packet(seq, payload)

            # Process feedback while sending
            self.process_feedback()

            time.sleep(self.interval)

        print("[SENDER] Waiting for remaining ACKs...")

        deadline = time.time() + (
            self.timeout * (self.max_retries + 2)
        )

        while self.pending and time.time() < deadline:

            self.process_feedback()
            self.check_retransmissions()

        # Count anything still pending as failed
        for seq in list(self.pending):
            print(f"[SENDER] Unacknowledged seq={seq}")
            self.stats["failed"] += 1
            del self.pending[seq]

        self.print_stats()

    def print_stats(self):

        print("\n========== SENDER STATISTICS ==========")
        print(f"Packets sent       : {self.stats['sent']}")
        print(f"ACKs received      : {self.stats['acknowledged']}")
        print(f"Retransmissions    : {self.stats['retransmissions']}")
        print(f"Unrecovered packets: {self.stats['failed']}")
        print("=======================================\n")

    def close(self):
        self.socket.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Team 11 UDP Sender"
    )

    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=5)

    args = parser.parse_args()

    sender = UDPSender(
        receiver_host=args.host,
        receiver_port=args.port,
        timeout=args.timeout,
        max_retries=args.retries
    )

    try:
        sender.send_stream(args.count)
    finally:
        sender.close()

