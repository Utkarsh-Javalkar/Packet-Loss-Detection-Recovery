
import json
import time

PROTOCOL_VERSION = 1

DATA = "DATA"
ACK = "ACK"
NACK = "NACK"
TELEMETRY = "TELEMETRY"

VALID_TYPES = {DATA, ACK, NACK, TELEMETRY}

MAX_DATAGRAM_SIZE = 60000


def encode_message(message_type, stream_id, seq=None, payload=None,
                   extra=None):
    """Convert a protocol message into UTF-8 JSON bytes."""

    if message_type not in VALID_TYPES:
        raise ValueError("Invalid message type")

    if not isinstance(stream_id, str) or not stream_id:
        raise ValueError("Invalid stream ID")

    message = {
        "version": PROTOCOL_VERSION,
        "type": message_type,
        "stream_id": stream_id,
        "timestamp": time.time()
    }

    if seq is not None:
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
            raise ValueError("Sequence number must be a non-negative integer")
        message["seq"] = seq

    if payload is not None:
        message["payload"] = payload

    if extra is not None:
        if not isinstance(extra, dict):
            raise ValueError("Extra fields must be a dictionary")
        message.update(extra)

    encoded = json.dumps(message, separators=(",", ":")).encode("utf-8")

    if len(encoded) > MAX_DATAGRAM_SIZE:
        raise ValueError("Message exceeds maximum UDP payload size")

    return encoded


def decode_message(data):
    """Validate and decode a received protocol message."""

    if not isinstance(data, bytes):
        raise ValueError("Input must be bytes")

    if not data or len(data) > MAX_DATAGRAM_SIZE:
        raise ValueError("Invalid datagram size")

    try:
        message = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Invalid JSON message")

    if not isinstance(message, dict):
        raise ValueError("Message must be a JSON object")

    if message.get("version") != PROTOCOL_VERSION:
        raise ValueError("Unsupported protocol version")

    if message.get("type") not in VALID_TYPES:
        raise ValueError("Unknown message type")

    if not isinstance(message.get("stream_id"), str) or not message["stream_id"]:
        raise ValueError("Invalid stream ID")

    timestamp = message.get("timestamp")
    if (not isinstance(timestamp, (int, float))
            or isinstance(timestamp, bool)
            or timestamp <= 0):
        raise ValueError("Invalid timestamp")

    message_type = message["type"]

    if message_type in {DATA, ACK, NACK}:
        seq = message.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
            raise ValueError("Invalid sequence number")

    if message_type == DATA and not isinstance(message.get("payload"), str):
        raise ValueError("DATA message requires a string payload")

    return message

