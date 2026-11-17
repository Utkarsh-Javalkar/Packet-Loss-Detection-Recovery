# Team 11 — Packet Loss Detection and Recovery Using UDP

A local educational prototype combining application-level UDP recovery with OS-Ken/OpenFlow 1.3 path control in Mininet.

## Environment verified by the team

- Ubuntu 26.04 guest in VirtualBox
- Python 3.11.18 project virtual environment
- OS-Ken 3.1.1
- Mininet 2.3.0
- Open vSwitch 3.7.1

The Eventlet deprecation warning printed by OS-Ken 3.1.1 is known in this environment; it is not by itself a controller startup failure.

## Architecture

- Sender: `10.0.0.1:5000`
- Receiver: `10.0.0.2:5001`
- OS-Ken OpenFlow endpoint: `127.0.0.1:6653`
- Receiver telemetry endpoint: `10.0.0.254:6000`
- Telemetry source is validated as `10.0.0.2:5001`.
- Primary route: `h1-s1-s2-h2`.
- Alternate route: `h1-s1-s3-s2-h2`.

See `docs/architecture.md` for the link/port map.

## 1. Setup

```bash
cd ~/Packet-Loss-Detection-Recovery
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -r requirements.txt
```

This uses the verified Python 3.11 toolchain and installs packages directly into the project virtual environment. Mininet and Open vSwitch are system packages and must already be installed. Do not run the Mininet topology using the virtual environment Python; use system `sudo python3` as below.

## 2. Start OS-Ken (Terminal 1)

```bash
cd ~/Packet-Loss-Detection-Recovery
source .venv/bin/activate
PYTHONPATH=. osken-manager --ofp-tcp-listen-port 6653 controller.controller
```

Keep this terminal open. It should log the telemetry listener and switch connections.

## 3. Start Mininet (Terminal 2)

```bash
cd ~/Packet-Loss-Detection-Recovery
sudo mn -c
sudo python3 topology/mininet_topology.py
```

At `mininet>` run:

```text
pingall
```

Expected in a clean run: 0% dropped for h1/h2. Then start the receiver in the background:

```text
h2 python3 -m app.receiver --host 10.0.0.2 --port 5001 --sender-ip 10.0.0.1 --sender-port 5000 --telemetry-host 10.0.0.254 --telemetry-port 6000 --grace 0.35 > /tmp/team11_receiver.log 2>&1 &
```

Start the sender:

```text
h1 python3 -m app.sender --bind-host 10.0.0.1 --bind-port 5000 --host 10.0.0.2 --port 5001 --count 100 --interval 0.05 --timeout 0.8 --retries 4
```

`h2 cat /tmp/team11_receiver.log` displays receiver logs. The controller terminal shows accepted/rejected telemetry and route transitions.

## 4. Demonstrate loss-triggered rerouting

Start a fresh long stream so both path switching and failback can be observed during the same run. First apply loss to the primary direction:

```text
s1 tc qdisc replace dev s1-eth2 root netem loss 15%
```

Then start the sender in the background (600 packets at 50 ms intervals is approximately 30 seconds of offered traffic):

```text
h1 python3 -m app.sender --bind-host 10.0.0.1 --bind-port 5000 --host 10.0.0.2 --port 5001 --count 600 --interval 0.05 --timeout 0.8 --retries 4 > /tmp/team11_sender_loss.log 2>&1 &
```

The receiver reports confirmed missing packets after the reordering grace. Two consecutive reports at or above the configured 10% trigger should cause OS-Ken to install alternate route flows. Once the controller log shows `PATH CHANGE PRIMARY -> ALTERNATE`, verify the flow tables:

```text
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s2
sh ovs-ofctl -O OpenFlow13 dump-flows s3
```

Now remove the primary impairment while the sender is still running:

```text
s1 tc qdisc del dev s1-eth2 root
```

After loss stays at or below 2% for the 5-second hold-down, OS-Ken should restore the primary path. Verify the second `PATH CHANGE ALTERNATE -> PRIMARY` controller log and dump the flows again. These thresholds are configurable using environment variables documented below.

## 5. Useful configuration environment variables

- `TEAM11_TELEMETRY_PORT` (default 6000)
- `TEAM11_RECEIVER_IP` (default 10.0.0.2)
- `TEAM11_RECEIVER_PORT` (default 5001)
- `TEAM11_LOSS_TRIGGER` (default 10 percent)
- `TEAM11_TRIGGER_SAMPLES` (default 2)
- `TEAM11_RECOVERY_THRESHOLD` (default 2 percent)
- `TEAM11_HOLD_DOWN` (default 5 seconds)
- `TEAM11_TELEMETRY_MAX_AGE` (default 10 seconds)

Example before starting controller:

```bash
TEAM11_LOSS_TRIGGER=10 TEAM11_TRIGGER_SAMPLES=2 TEAM11_HOLD_DOWN=5 PYTHONPATH=. osken-manager --ofp-tcp-listen-port 6653 controller.controller
```

## 6. Tests and results

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/local_loss_demo.py
```

The local loss demo deterministically drops the first DATA sequence 2 through a loopback proxy and verifies NACK/retransmission. It is a local app test, not a substitute for the Mininet/tc-netem integration test. The STP contains 20 cases. `tests/test_execution_template.csv` starts with every case Pending. Record actual results, logs, and screenshots before changing any status. The project package does not claim all STP cases have passed. For performance evaluation, repeat static and SDN-assisted runs with identical offered load under 1%, 5%, and 15% impairment, record raw measurements under `results/data/`, and produce graphs/tables under `results/`.

## 7. Cleanup

At the `mininet>` prompt:

```text
exit
```

Then clean stale Mininet state:

```bash
sudo mn -c
```

If the qdisc is still present and the topology is active, remove it before exit with `s1 tc qdisc del dev s1-eth2 root`.

## Safety and scope

Run only in the isolated Ubuntu/VirtualBox Mininet lab. Do not expose OpenFlow or telemetry ports to untrusted networks. The prototype validates telemetry structure, source endpoint, timestamp freshness, and monotonically increasing report IDs; it is not production authentication or encryption.


## 8. Submission documentation and evidence

- `docs/Team11_SRS_Final.docx` and `docs/Team11_STP_Final.docx`: team-approved source documents supplied for this submission.
- `docs/IMPLEMENTATION_CONFIGURATION_RECORD.md`: observed environment, address/port plan, message fields, thresholds and timer values closing the SRS TBD list.
- `docs/architecture_diagram.png` and `docs/architecture.md`: verified topology and switch-port mapping.
- `docs/Developer_Execution_Report.docx`: developer smoke/integration observations; not a substitute for formal STP sign-off.
- `docs/evidence/`: screenshots and evidence index.
- `tests/developer_execution_record.csv`: supplementary per-case evidence assessment. The formal STP remains the controlling test plan.
