# Business Requirements Specification (BRS)

**Product:** adaptive multi-criteria data routing for heterogeneous oil and gas telecom links.
**Status:** written from the submitted abstract (paper 27OE-P-17-SPE) and the code in this repository.
The owner has not reviewed it.

## 1. Business problem
Offshore platforms and remote fields reach the control centre over several links with very different
cost, delay and reliability (industrial Ethernet or microwave, 5G, satellite). A static
primary/backup rule sends all traffic over the best link, so cheap capacity sits idle and bulk traffic
pays the price of control traffic, and recovery waits for timers.

## 2. Objectives
| ID | Objective |
|----|-----------|
| BO-1 | Keep control commands and safety alarms on the most reliable low-delay path and recover from a link fault in well under a second |
| BO-2 | Send bulk and monitoring traffic over the cheapest adequate link |
| BO-3 | Avoid needless switching caused by measurement noise |
| BO-4 | Make the choice explainable: criteria weights come from stated judgments (Fuzzy AHP), not a black box |
| BO-5 | State which results come from simulation and which from hardware |

## 3. Stakeholders
Telecom and automation engineers of the operator, OT security, plant management (cost), the owner.

## 4. Scope
In: link scoring, stream classification, failover logic, simulation study. Out: packet-level forwarding
in a router or SD-WAN device, security controls, real link measurements.

## 5. Constraints and assumptions
- All link parameters, cost units and fault statistics are assumed (docs/SRS.md section 6).
- Failover speed depends on link-layer fault signalling (for example BFD), which is a parameter here.
- Do not publish method details covered by filed claims.

## 6. Success measures (to be measured on real links)
Critical-stream availability, packets lost per fault, time to recover per fault type, cost per month
against a static baseline, switching events per day.
