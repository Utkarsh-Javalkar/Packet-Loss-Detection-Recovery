# Team 11 architecture and port map

## Data and control architecture

- UDP DATA/ACK/NACK: `h1 (10.0.0.1:5000) <-> h2 (10.0.0.2:5001)` through Open vSwitch.
- Loss telemetry: receiver `h2` sends JSON UDP reports from `10.0.0.2:5001` to `10.0.0.254:6000`.
- The `ctrl` management host uses `inNamespace=False`; its `ctrl-eth0` interface is in the Ubuntu root namespace so the OS-Ken UDP listener can receive telemetry.
- OS-Ken controls the three OVS switches over OpenFlow 1.3 on TCP port 6653.

## Switch port map (fixed by topology link creation order)

| Switch | Port | Connected device | Purpose |
|---|---:|---|---|
| s1 | 1 | h1 | Sender |
| s1 | 2 | s2 | Primary path |
| s1 | 3 | s3 | Alternate path |
| s1 | 4 | ctrl | Telemetry endpoint |
| s2 | 1 | h2 | Receiver |
| s2 | 2 | s1 | Primary path |
| s2 | 3 | s3 | Alternate path |
| s3 | 1 | s1 | Alternate path |
| s3 | 2 | s2 | Alternate path |

## Route behaviour

- Primary: `h1 -> s1 -> s2 -> h2`; reverse direction uses `s2 -> s1`.
- Alternate: `h1 -> s1 -> s3 -> s2 -> h2`; reverse direction follows the reverse links.
- Telemetry always uses the alternate links, so loss or failure on the primary s1-s2 link does not block reports to the controller.
- Trigger defaults: 10% loss for two consecutive reports; recovery threshold 2% sustained for 5 seconds. These are experimental defaults, not measured optimal values.

## Message sequence

1. Sender sends DATA with `stream_id`, monotonic `seq`, timestamp and payload.
2. Receiver ACKs each unique DATA and duplicate; duplicate payload is not delivered twice.
3. A sequence gap is held for the grace period; confirmed gaps receive NACK.
4. Sender retries on NACK or timeout up to the retry limit.
5. Receiver periodically sends a TELEMETRY JSON report; controller validates source, fields, freshness and report ID.
6. Sustained high loss changes OVS flows to alternate; sustained healthy reports after the hold-down return to primary.
