"""Pure validation function for receiver-to-controller telemetry."""
import time


def validate_telemetry(msg, addr, expected_source, max_age, last_reports, now=None):
    """Return (valid, reason). last_reports maps stream_id -> (report_id, timestamp)."""
    now = time.time() if now is None else now
    if addr != expected_source:
        return False, f"unauthorized source {addr}"
    if not isinstance(msg, dict):
        return False, "payload is not an object"
    required = {"version", "type", "stream_id", "timestamp", "report_id",
                "window_expected", "window_received", "loss_pct", "last_received_seq"}
    if not required.issubset(msg):
        return False, "missing telemetry fields"
    if msg.get("version") != 1 or msg.get("type") != "TELEMETRY":
        return False, "invalid version/type"
    if not isinstance(msg.get("stream_id"), str) or not msg["stream_id"]:
        return False, "invalid stream_id"
    for key in ("report_id", "window_expected", "window_received", "last_received_seq"):
        if not isinstance(msg.get(key), int) or isinstance(msg.get(key), bool):
            return False, f"invalid {key} type"
    if msg["report_id"] <= 0 or msg["window_expected"] <= 0 or msg["last_received_seq"] < 0:
        return False, "invalid report/window count"
    if not 0 <= msg["window_received"] <= msg["window_expected"]:
        return False, "window_received outside permitted range"
    loss = msg.get("loss_pct")
    if not isinstance(loss, (int, float)) or isinstance(loss, bool) or not 0 <= loss <= 100:
        return False, "loss_pct outside 0..100"
    ts = msg.get("timestamp")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return False, "invalid timestamp"
    age = now - ts
    if age < -2 or age > max_age:
        return False, f"stale/future telemetry age={age:.2f}s"
    previous_id, previous_ts = last_reports.get(msg["stream_id"], (0, 0.0))
    if msg["report_id"] <= previous_id:
        return False, "old/replayed report_id"
    if ts <= previous_ts:
        return False, "older/replayed timestamp"
    return True, "ok"
