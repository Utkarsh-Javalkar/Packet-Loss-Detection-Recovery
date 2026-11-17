# Developer smoke-test evidence (isolated build environment)

These checks were executed against the generated application package in an isolated Python environment, not on the team's Ubuntu/Mininet VM. They are implementation smoke tests only and do not change the STP execution status.

1. `python -m compileall -q app controller topology tests` — completed without syntax errors.
2. `python -m unittest discover -s tests -p 'test_*.py' -v` — 11 automated tests passed: 6 protocol tests (DATA, ACK, NACK, TELEMETRY round trips and invalid-input checks) plus 5 pure telemetry validation tests (valid report, malformed/out-of-range fields, unexpected source, stale report, replayed ID/timestamp).
3. Loopback UDP run: 10 original DATA packets, 10 ACKs, 0 retransmissions and 0 unrecovered packets.
4. Deterministic local fault-proxy run: first transmission of sequence 2 dropped; receiver emitted NACK; sender retransmitted sequence 2 once; receiver ACKed it; 5/5 packets acknowledged, 0 unrecovered, 20% retransmission overhead.

Not verified in this isolated environment: OS-Ken runtime, OpenFlow switch connection, Mininet topology/port numbers, telemetry namespace reachability, OVS path transitions, tc-netem behaviour, failback, performance profiles, security test cases. These must be verified on the target VM before reporting corresponding STP cases as PASS.
