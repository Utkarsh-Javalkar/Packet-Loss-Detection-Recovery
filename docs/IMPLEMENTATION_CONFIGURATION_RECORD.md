# Implementation configuration record — Team 11

This record captures the concrete implementation values observed in the Ubuntu/VirtualBox demonstration on 17 November 2026. It supplements the SRS Appendix C TBD list; it does not change the SRS requirements or claim that every requirement has passed acceptance testing.

## TBD closure summary

| SRS TBD | Implemented / observed value | Closure evidence / note |
|---|---|---|
| TBD-01 — Ubuntu and Python | Ubuntu 26.04 LTS guest; Python 3.11.18 project virtual environment | Environment check screenshot and developer execution report |
| TBD-02 — Mininet, OVS and OS-Ken versions | Mininet 2.3.0; Open vSwitch 3.7.1; OS-Ken 3.1.1 | Version commands captured before integration run |
| TBD-03 — topology, switch ports and host IPs | Hosts h1=10.0.0.1 and h2=10.0.0.2; switches s1/s2/s3; management host ctrl=10.0.0.254 | Port map below and `architecture_diagram.png`; Mininet `pingall` observed 0% dropped |
| TBD-04 — telemetry endpoint | UDP listener 10.0.0.254:6000; configured receiver source 10.0.0.2:5001 | OS-Ken logged accepted telemetry reports from Mininet receiver |
| TBD-05 — message format and ports | UTF-8 JSON; app sender 10.0.0.1:5000; receiver 10.0.0.2:5001; telemetry UDP 10.0.0.254:6000; OpenFlow TCP 127.0.0.1:6653 | Protocol module and config/settings.json |
| TBD-06 — loss trigger/window | Trigger: loss >=10% for 2 consecutive telemetry reports; telemetry interval default 1.0 s; recovery threshold <=2% sustained for 5.0 s; telemetry max age 10 s | Settings and controller log transitions; experimental defaults, not optimized values |
| TBD-07 — retransmission timing/retries | Reordering grace 0.35 s; sender ACK timeout 0.8 s; maximum retries 4 | config/settings.json and sender/receiver command defaults |

## Protocol message fields

All protocol messages are UTF-8 JSON datagrams with `version`, `type`, `stream_id`, and `timestamp`. DATA adds `seq` and string `payload`; ACK and NACK add `seq`; TELEMETRY adds `report_id`, `window_expected`, `window_received`, `loss_pct`, and `last_received_seq`. Protocol version is 1. The implementation enforces a maximum encoded datagram size of 60,000 bytes.

## Switch-port map

| Switch | Port | Connected endpoint | Role |
|---|---:|---|---|
| s1 | 1 | h1 | Sender access |
| s1 | 2 | s2 port 2 | Primary DATA path |
| s1 | 3 | s3 port 1 | Alternate DATA path |
| s1 | 4 | ctrl | Telemetry management path |
| s2 | 1 | h2 | Receiver access |
| s2 | 2 | s1 port 2 | Primary DATA path |
| s2 | 3 | s3 port 2 | Alternate DATA path |
| s3 | 1 | s1 port 3 | Alternate DATA path |
| s3 | 2 | s2 port 3 | Alternate DATA path |

Primary DATA route: `h1 → s1 → s2 → h2`. Alternate DATA route: `h1 → s1 → s3 → s2 → h2`. Telemetry uses the management path from h2 through s2/s3/s1 to ctrl; it is separate from the primary DATA link being impaired.

## Important interpretation

These values describe the current implementation and observed test environment. They are not a claim that the provisional thresholds are optimal or that all associated STP cases have passed. Formal verification, hard-link-failure testing, timeout/lost-ACK/duplicate/receiver-absence cases, and the three-profile static-versus-SDN performance evaluation remain separate test activities.
