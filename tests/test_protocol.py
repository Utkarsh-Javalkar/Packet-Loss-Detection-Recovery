import unittest
from app.protocol import DATA, ACK, NACK, TELEMETRY, encode_message, decode_message

class ProtocolTests(unittest.TestCase):
    def test_data_round_trip(self):
        self.assertEqual(decode_message(encode_message(DATA, 'team11', 1, 'hello'))['payload'], 'hello')
    def test_ack_round_trip(self):
        self.assertEqual(decode_message(encode_message(ACK, 'team11', 7))['seq'], 7)
    def test_nack_round_trip(self):
        self.assertEqual(decode_message(encode_message(NACK, 'team11', 8))['type'], NACK)
    def test_telemetry_round_trip(self):
        m = decode_message(encode_message(TELEMETRY, 'team11', extra={'report_id': 1, 'window_expected': 10, 'window_received': 8, 'loss_pct': 20.0}))
        self.assertEqual(m['report_id'], 1)
    def test_reject_invalid_json(self):
        with self.assertRaises(ValueError): decode_message(b'{bad')
    def test_reject_negative_seq(self):
        with self.assertRaises(ValueError): encode_message(DATA, 'team11', -1, 'x')

if __name__ == '__main__': unittest.main()
