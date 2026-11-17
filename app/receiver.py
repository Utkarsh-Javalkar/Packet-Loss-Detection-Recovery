
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


class UDPReceiver:
    def __init__(self, host="127.0.0.1", port=5001,
                 sender_port=5000, grace_period=0.5):

        self.host = host
        self.port = port
        self.sender_port = sender_port
        self.grace_period = grace_period

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.socket.settimeout(0.1)

        self.received = set()
        self.pending = {}
        self.highest_seq = 0

        self.stats = {
            "unique_received": 0,
            "duplicates": 0,
            "missing": 0
        }

        print(f"[RECEIVER] Listening on {self.host}:{self.port}")

    def send_feedback(self, message_type, seq, address):
        message = encode_message(
            message_type,
            "team11",
            seq
        )
        self.socket.sendto(message, address)

        print(f"[RECEIVER] Sent {message_type} for seq={seq}")

    def process_data(self, message, address):

        seq = message["seq"]

        # Duplicate detection
        if seq in self.received:
            self.stats["duplicates"] += 1
            print(f"[RECEIVER] Duplicate packet: {seq}")
            self.send_feedback(ACK, seq, address)
            return

        self.received.add(seq)
        self.stats["unique_received"] += 1

        print(
            f"[RECEIVER] Received seq={seq}, "
            f"payload={message['payload']}"
        )

        # Detect sequence gaps
        if seq > self.highest_seq + 1:
            for missing_seq in range(self.highest_seq + 1, seq):
                if missing_seq not in self.received:
                    self.pending[missing_seq] = time.time()
                    self.stats["missing"] += 1
                    print(
                        f"[RECEIVER] Missing sequence detected: "
                        f"{missing_seq}"
                    )

        self.highest_seq = max(self.highest_seq, seq)

        # Clear a gap if its packet arrives later
        self.pending.pop(seq, None)

        self.send_feedback(ACK, seq, address)

    def check_missing(self, address):
        now = time.time()

        expired = [
            seq for seq, detected_at in self.pending.items()
            if now - detected_at >= self.grace_period
        ]

        for seq in expired:
            print(f"[RECEIVER] Confirmed missing seq={seq}")
            self.send_feedback(NACK, seq, address)
            del self.pending[seq]

    def print_stats(self):
        print("\n========== RECEIVER STATISTICS ==========")
        print(f"Unique received : {self.stats['unique_received']}")
        print(f"Duplicates      : {self.stats['duplicates']}")
        print(f"Missing detected: {self.stats['missing']}")
        print("=========================================\n")

    def run(self):
        print("[RECEIVER] Waiting for UDP packets...")

        last_stats = time.time()
        sender_address = None

        try:
            while True:
                try:
                    data, address = self.socket.recvfrom(65535)
                    sender_address = address

                    try:
                        message = decode_message(data)

                        if message["type"] == DATA:
                            self.process_data(message, address)

                    except ValueError as error:
                        print(f"[RECEIVER] Invalid packet: {error}")

                except socket.timeout:
                    pass

                if sender_address is not None:
                    self.check_missing(sender_address)

                if time.time() - last_stats >= 5:
                    self.print_stats()
                    last_stats = time.time()

        except KeyboardInterrupt:
            print("\n[RECEIVER] Shutting down.")
            self.print_stats()

        finally:
            self.socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Team 11 UDP Receiver"
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--grace", type=float, default=0.5)

    args = parser.parse_args()

    receiver = UDPReceiver(
        host=args.host,
        port=args.port,
        grace_period=args.grace
    )

    receiver.run()

