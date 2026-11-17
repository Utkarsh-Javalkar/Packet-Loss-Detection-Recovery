# Team 11 — 5–7 minute demonstration script

## Before starting
- Use the Ubuntu VirtualBox guest in the isolated Mininet environment.
- Ensure no stale Mininet state or `tc netem` impairment remains (`sudo mn -c`; confirm/clear qdisc in the topology if it is active).
- Keep two terminals available: OS-Ken and Mininet.

## Demonstration sequence
1. **Start OS-Ken**
   ```bash
   cd ~/Packet-Loss-Detection-Recovery
   source .venv/bin/activate
   PYTHONPATH=. osken-manager --ofp-tcp-listen-port 6653 controller.controller
   ```
   Point out OpenFlow 1.3, the telemetry listener on UDP 6000, and switch connection messages.
2. **Start Mininet**
   ```bash
   cd ~/Packet-Loss-Detection-Recovery
   sudo mn -c
   sudo python3 topology/mininet_topology.py
   ```
   At `mininet>` run `pingall` and point out 0% loss in the observed baseline run.
3. **Show primary OpenFlow rules**
   ```text
   sh ovs-ofctl -O OpenFlow13 dump-flows s1
   sh ovs-ofctl -O OpenFlow13 dump-flows s2
   sh ovs-ofctl -O OpenFlow13 dump-flows s3
   ```
4. **Start receiver, then sender** (commands copied from README). Show ACKs, receiver counters and accepted telemetry.
5. **Inject primary-path loss and run a continuous sender stream** (commands copied from README). Show telemetry loss reports, `PATH CHANGE PRIMARY -> ALTERNATE`, alternate-rule installation and delivery confirmation.
6. **Remove impairment while the stream is running**. Show `PATH CHANGE ALTERNATE -> PRIMARY` after healthy telemetry and hold-down.
7. **Conclude with measured packet statistics**: originals, transmissions, ACKs, retransmissions, unrecovered packets, and the fact that full 20-case STP/performance coverage is still recorded separately.

## Demonstrated values from the 17 November developer run
- Local deterministic loss demo: 5 original DATA, 1 retransmission, 5 ACKs, 0 unrecovered.
- Clean Mininet run: 100 original DATA, 100 ACKs, 0 retransmissions, 0 unrecovered.
- Loss-triggered run: 600 original DATA, 76 retransmissions, 600 ACKs, 0 unrecovered; controller logged 1.052 s delivery confirmation after reroute.
- Clean follow-up/failback run: 240 original DATA, 1 retransmission, 240 ACKs, 0 unrecovered; receiver unique=240, missing_detected=1, recovered=1, currently_missing=0.

These are observed demonstration runs, not a complete static-vs-SDN performance evaluation.
