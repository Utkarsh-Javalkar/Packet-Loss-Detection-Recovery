# Evidence index — Team 11

Evidence was captured during developer smoke/integration runs on 17 November 2026. Original screenshots are retained in `screenshots/`. This evidence index is supplementary to the formal STP; the tester should independently review and sign off the test cases.

## Environment observed

- Ubuntu 26.04 LTS guest in VirtualBox
- Python 3.11.18 project virtual environment
- OS-Ken 3.1.1
- Mininet 2.3.0
- Open vSwitch 3.7.1

## Screenshot index

- `01_automated_tests_and_environment.png` — 11 automated protocol/telemetry tests completed with OK output; Python/OS-Ken dependency context.
- `02_local_nack_retransmission.png` — Deterministic local proxy drops original DATA seq=2; receiver gap/NACK; sender retransmits; 0 unrecovered.
- `03_osken_switch_connections.png` — OS-Ken custom app starts; telemetry listener and OpenFlow switches s1/s2/s3 connect.
- `04_mininet_pingall.png` — Mininet topology reports 0% dropped (6/6 received).
- `05_primary_flow_tables.png` — OpenFlow 1.3 flow table dump for s1, s2 and s3 during primary-path operation.
- `06_controller_initial_telemetry.png` — Controller accepts receiver telemetry reports with 0% measured loss.
- `07_600_packet_sender_run.png` — 600-packet sender run output; final detailed summary also recorded separately in report.
- `08_reroute_and_recovery_logs.png` — 15% qdisc run: loss reports 16.22% and 18.79%; PRIMARY to ALTERNATE; delivery confirmation; later failback and subsequent re-trigger while impairment still active.
- `09_clean_stream_sender_stats.png` — 240-packet clean follow-up: 240 ACKs, one retransmission, zero unrecovered.
- `10_failback_and_final_telemetry.png` — Controller confirms ALTERNATE to PRIMARY after 5-second healthy hold-down and later clean telemetry.
- `11_final_primary_flows_receiver_stats.png` — Final primary-path s1 flow-table dump and receiver stats: unique=240, duplicates=0, missing_detected=1, recovered=1, currently_missing=0.

## Important limitations

- The 11 automated tests cover protocol and telemetry-validation unit tests; they are not 11 of the 20 formal STP cases.
- The alternate-path installation/change is visible in controller logs, but a dedicated alternate-active `ovs-ofctl dump-flows` capture was not archived.
- TC06–TC09, TC17 and TC18 were not executed in the observed session.
- TC19–TC20 were exercised at helper/unit-test level only, not by injecting malformed/unauthorized reports into the running controller and verifying unchanged flow tables.
- Performance comparisons across 1%, 5%, and 15% static-vs-SDN profiles, with goodput and recovery metrics, remain pending.
- Do not mark remaining STP cases PASS without actual execution evidence.