# Team 11 — Project Submission Status

**Project:** Packet Loss Detection and Recovery Using UDP  
**Team:** 11  
**Institution:** PES University  
**Last Updated:** 20 November 2026

---

## 1. Project Overview

This project implements packet-loss detection and recovery using UDP, combined with Software-Defined Networking (SDN) for dynamic path switching.

The system consists of:
- UDP sender and receiver applications.
- Sequence-number-based packet tracking.
- ACK/NACK feedback and retransmission.
- OS-Ken SDN controller.
- Open vSwitch switches using OpenFlow 1.3.
- Mininet topology with primary and alternate paths.
- Telemetry-based loss monitoring and dynamic rerouting.

## 2. Implementation Status

| Component | Status |
|---|---|
| UDP sender | Implemented |
| UDP receiver | Implemented |
| DATA, ACK and NACK protocol | Implemented |
| Sequence number tracking | Implemented |
| Retransmission buffer | Implemented |
| Timeout-based retransmission | Implemented |
| OS-Ken controller | Implemented |
| Receiver-to-controller telemetry | Implemented |
| OpenFlow 1.3 flow programming | Implemented |
| Mininet topology | Implemented |
| Primary and alternate paths | Implemented |
| Loss-triggered rerouting | Demonstrated |
| Primary-path failback | Demonstrated |
| Automated unit tests | Executed successfully |

## 3. Verified Environment

The following environment was used during the developer execution:

| Component | Version |
|---|---|
| Operating System | Ubuntu 26.04 LTS |
| Python | 3.11.18 |
| OS-Ken | 3.1.1 |
| Mininet | 2.3.0 |
| Open vSwitch | 3.7.1 |
| OpenFlow | 1.3 |

## 4. Testing and Execution Results

### 4.1 Automated Unit Tests

The following test command was executed:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

**Observed result:** 11 tests passed, 0 failed.

These tests cover protocol message handling and telemetry validation.

### 4.2 Local Packet-Loss Demonstration

The local deterministic loss demonstration deliberately dropped the original DATA packet with sequence number 2.

Observed result:
- 5 original DATA packets.
- 1 retransmission.
- 5 ACKs received.
- 0 unrecovered packets.

The receiver detected the missing sequence number, sent a NACK, and successfully received the retransmitted packet.

### 4.3 Mininet Integration Demonstration

A clean Mininet stream was executed.

Observed result:
- 100 original DATA packets.
- 100 ACKs.
- 0 retransmissions.
- 0 unrecovered packets.

### 4.4 Loss-Triggered Rerouting

A 15% packet-loss impairment was applied to the primary path using `tc netem`.

Observed result:
- 600 original DATA packets.
- 676 total DATA transmissions.
- 600 ACKs.
- 76 retransmissions.
- 0 unrecovered packets.
- Controller switched from PRIMARY to ALTERNATE.
- Delivery confirmation was logged after the path change at 1.052 seconds.

The controller subsequently logged a transition from ALTERNATE to PRIMARY after the configured recovery condition was satisfied.

### 4.5 Clean Follow-Up and Failback

A subsequent clean stream was executed.

Observed result:
- 240 original DATA packets.
- 241 total DATA transmissions.
- 240 ACKs.
- 1 retransmission.
- 0 unrecovered packets.

The receiver reported:
- 240 unique packets received.
- 0 duplicates.
- 1 missing packet detected and recovered.
- 0 currently missing packets.

These are observations from individual demonstration runs, not a controlled performance benchmark.

## 5. STP Test Execution Summary

The STP contains 20 test cases. The following status reflects the evidence available from the developer execution session.

| Status | Number of test cases |
|---|---:|
| Demonstrated | 10 |
| Partial | 4 |
| Not Executed | 6 |
| **Total** | **20** |

### 5.1 Demonstrated

- TC01 — UDP stream with 0% loss.
- TC02 — Sequence gap detection.
- TC04 — ACK generation.
- TC05 — NACK and retransmission.
- TC10 — Mininet primary path.
- TC11 — Initial OpenFlow rules.
- TC12 — Telemetry delivery.
- TC13 — Loss-triggered reroute.
- TC15 — Continuous stream during reroute.
- TC16 — Primary recovery and failback.

### 5.2 Partial

- TC03 — Out-of-order packet handling.
- TC14 — Flow rule verification during alternate-path operation.
- TC19 — Malformed telemetry validation.
- TC20 — Unexpected-source or stale receiver telemetry.

### 5.3 Not Executed

- TC06 — Timeout-only retransmission.
- TC07 — Lost ACK handling.
- TC08 — Deliberate duplicate DATA.
- TC09 — Receiver unavailable.
- TC17 — Hard loss / primary-link cut.
- TC18 — Controlled performance profiles and static-path comparison.

**Note:** These are developer evidence assessments, not independent tester sign-off. Partial and unexecuted cases must not be treated as passed.

## 6. Known Limitations and Remaining Work

The following activities remain incomplete:

1. Dedicated timeout-only retransmission, lost ACK, duplicate packet and receiver-absence tests.
2. Capturing the alternate-path OpenFlow flow table while that path is active.
3. Dedicated primary-link failure testing.
4. End-to-end negative telemetry tests proving that invalid telemetry does not change forwarding rules.
5. Controlled static-path versus SDN-assisted performance comparisons under 1%, 5% and 15% packet-loss profiles.
6. Complete goodput and byte-based retransmission-overhead evaluation.
7. Independent tester review and sign-off of the remaining STP cases.

The prototype demonstrates the core packet recovery and SDN rerouting workflow, but the above limitations remain part of the testing record.

## 7. Repository Structure

The GitHub repository is organized as follows:

```text
Packet-Loss-Detection-Recovery/
│
├── app/
├── controller/
├── topology/
├── config/
├── tests/
├── results/
│   └── logs/
│
├── docs/
│   ├── Team11_SRS_v1.1.docx
│   ├── Team11_STP_v1.1.docx
│   ├── Developer_Execution_Report.docx
│   ├── IMPLEMENTATION_CONFIGURATION_RECORD.md
│   ├── architecture.md
│   ├── architecture_diagram.png
│   └── evidence/
│
├── requirements.txt
├── .gitignore
├── README.md
└── SUBMISSION_STATUS.md
```

## 8. Submission Documents and Evidence

The repository contains or is intended to contain:

- Software Requirements Specification (SRS).
- Software Test Plan (STP).
- Developer Execution Report.
- Implementation Configuration Record.
- Network architecture diagram and port mapping.
- Application and controller source code.
- Automated test scripts.
- Execution logs and screenshots.
- README with setup and demonstration instructions.

The SRS and STP are maintained as separate documents. The Developer Execution Report records the observed implementation and test evidence; it does not replace the STP.

## 9. Final Status

The core UDP packet-loss detection and recovery prototype has been implemented and demonstrated in Mininet with OS-Ken and OpenFlow 1.3.

Application-level retransmission, receiver telemetry, loss-triggered alternate-path switching, delivery confirmation and primary-path failback were observed during developer execution.

The automated unit test suite passed all 11 tests. The remaining STP cases and complete performance evaluation are documented above and are not claimed as completed.

---

**Team 11**  
**Packet Loss Detection and Recovery Using UDP**  
**PES University**
