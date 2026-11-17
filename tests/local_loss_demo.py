"""Local deterministic loss test: drops the first DATA seq=2, then verifies NACK retry."""
import argparse
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from app.protocol import decode_message


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sender-port', type=int, default=19500)
    p.add_argument('--receiver-port', type=int, default=19501)
    p.add_argument('--proxy-port', type=int, default=19502)
    args = p.parse_args()
    sender_addr = ('127.0.0.1', args.sender_port)
    receiver_addr = ('127.0.0.1', args.receiver_port)
    proxy_addr = ('127.0.0.1', args.proxy_port)
    relay_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    relay_sock.bind(proxy_addr)
    relay_sock.settimeout(0.2)
    state = {'sender': None, 'dropped': False, 'stop': False, 'nack_seen': False}

    def relay():
        while not state['stop']:
            try:
                data, addr = relay_sock.recvfrom(65535)
            except socket.timeout:
                continue
            try:
                msg = decode_message(data)
            except ValueError:
                continue
            if msg['type'] == 'DATA':
                state['sender'] = addr
                if msg['seq'] == 2 and not state['dropped']:
                    state['dropped'] = True
                    print('[PROXY] Dropped first original DATA seq=2')
                    continue
                relay_sock.sendto(data, receiver_addr)
            elif msg['type'] in ('ACK', 'NACK') and state['sender']:
                if msg['type'] == 'NACK' and msg['seq'] == 2:
                    state['nack_seen'] = True
                relay_sock.sendto(data, state['sender'])

    worker = threading.Thread(target=relay, daemon=True)
    worker.start()
    receiver = subprocess.Popen(
        [sys.executable, '-u', '-m', 'app.receiver', '--host', '127.0.0.1',
         '--port', str(args.receiver_port), '--sender-ip', '127.0.0.1',
         '--sender-port', str(args.proxy_port), '--grace', '0.15'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(0.4)
        sender = subprocess.run(
            [sys.executable, '-m', 'app.sender', '--bind-host', '127.0.0.1',
             '--bind-port', str(args.sender_port), '--host', '127.0.0.1',
             '--port', str(args.proxy_port), '--count', '5', '--interval', '0.03',
             '--timeout', '0.5', '--retries', '3'],
            capture_output=True, text=True, timeout=10)
    finally:
        state['stop'] = True
        relay_sock.close()
        receiver.terminate()
        try:
            receiver_output = receiver.communicate(timeout=2)[0]
        except subprocess.TimeoutExpired:
            receiver.kill()
            receiver_output = receiver.communicate()[0]

    print('\n--- SENDER OUTPUT ---')
    print(sender.stdout)
    print('--- RECEIVER OUTPUT ---')
    print(receiver_output)
    if sender.returncode != 0 or not state['dropped'] or not state['nack_seen']:
        print('[TEST] FAIL: expected deterministic NACK/retransmission was not observed')
        return 1
    if 'Retransmissions     : 1' not in sender.stdout or 'Unrecovered packets : 0' not in sender.stdout:
        print('[TEST] FAIL: sender counters did not match expected recovery')
        return 1
    print('[TEST] PASS: first seq=2 was dropped; NACK and one retransmission recovered it.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
