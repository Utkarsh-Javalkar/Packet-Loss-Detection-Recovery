import time
import unittest
from controller.telemetry_validation import validate_telemetry

EXPECTED = ('10.0.0.2', 5001)
BASE = {
    'version': 1, 'type': 'TELEMETRY', 'stream_id': 'team11',
    'timestamp': 1000.0, 'report_id': 1,
    'window_expected': 10, 'window_received': 8,
    'loss_pct': 20.0, 'last_received_seq': 10,
}

class TelemetryValidationTests(unittest.TestCase):
    def test_valid_report(self):
        ok, reason = validate_telemetry(dict(BASE), EXPECTED, EXPECTED, 10, {}, now=1001)
        self.assertTrue(ok, reason)

    def test_unexpected_source_rejected(self):
        ok, reason = validate_telemetry(dict(BASE), ('10.0.0.9', 5001), EXPECTED, 10, {}, now=1001)
        self.assertFalse(ok)
        self.assertIn('unauthorized', reason)

    def test_malformed_and_out_of_range_rejected(self):
        m = dict(BASE); m['loss_pct'] = 101
        ok, _ = validate_telemetry(m, EXPECTED, EXPECTED, 10, {}, now=1001)
        self.assertFalse(ok)
        m = dict(BASE); del m['report_id']
        ok, _ = validate_telemetry(m, EXPECTED, EXPECTED, 10, {}, now=1001)
        self.assertFalse(ok)

    def test_stale_report_rejected(self):
        ok, reason = validate_telemetry(dict(BASE), EXPECTED, EXPECTED, 10, {}, now=2000)
        self.assertFalse(ok)
        self.assertIn('stale', reason)

    def test_old_report_id_or_timestamp_rejected(self):
        m = dict(BASE); m['report_id'] = 2; m['timestamp'] = 1000.5
        ok, _ = validate_telemetry(m, EXPECTED, EXPECTED, 10, {'team11': (1, 1000.7)}, now=1001)
        self.assertFalse(ok)
        m = dict(BASE); m['report_id'] = 1; m['timestamp'] = 1000.9
        ok, _ = validate_telemetry(m, EXPECTED, EXPECTED, 10, {'team11': (1, 1000.7)}, now=1001)
        self.assertFalse(ok)

if __name__ == '__main__': unittest.main()
