# Performance evaluation protocol (TC18 / REQ-EVAL-01..06)

Perform on the target VM after the functional integration is stable. Do not fill result values in advance.

For each profile (light 1%, medium 5%, heavy 15%):

1. Restore the primary route and confirm sender/receiver are reachable.
2. Run the static-path baseline with `s1-eth2` impairment and the same sender count, interval, payload size, and duration that will be used for the SDN-assisted run. Disable controller-triggered path switching for the baseline only if implemented as a documented run mode; otherwise capture a static baseline before enabling the controller app.
3. Record original DATA sent, first-pass loss estimate, unique delivered payloads, retransmission count/bytes, unrecovered packets, elapsed time, and goodput.
4. Restore a clean topology and run the same traffic profile with controller rerouting enabled.
5. Record the time the loss threshold is satisfied, time alternate rules are observed, first successful delivery after the switch, path transitions, application retransmission recovery time, retransmission overhead, and goodput.
6. Save raw measurements to `results/data/` and graphs/tables to `results/`.

Suggested qdisc commands from the Mininet CLI:

```text
s1 tc qdisc replace dev s1-eth2 root netem loss 1%
s1 tc qdisc replace dev s1-eth2 root netem loss 5%
s1 tc qdisc replace dev s1-eth2 root netem loss 15%
s1 tc qdisc del dev s1-eth2 root
```

The three profiles are experimental settings, not guaranteed packet loss measurements. Use measured output, not the configured qdisc percentage, as the reported result.
