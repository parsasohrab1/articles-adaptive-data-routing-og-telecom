# Software Requirements Specification (SRS)

Every requirement names the module and the test that evidences it.

## 1. Architecture
Monitor (link state) -> classifier (criticality) -> Fuzzy AHP decision (utility per link) -> adaptive
router (event-driven failover for critical streams, timeout-based switching with damping for
non-critical streams). This repository implements the decision and routing logic and a fault
simulator; there is no packet forwarding plane.

## 2. Functional requirements
| ID | Requirement | Module | Test |
|----|-------------|--------|------|
| FR-1 | Compute criteria weights from fuzzy pairwise judgments; reject inconsistent judgments (CR > 0.1) | `fuzzy_ahp.py` | `test_fuzzy_ahp.py` |
| FR-2 | Separate weight profiles for critical and non-critical traffic | `fuzzy_ahp.py` | `test_profiles_are_consistent_and_normalised`, `test_profile_priorities` |
| FR-3 | Classify streams; unknown tags are critical | `classifier.py` | `test_classification` |
| FR-4 | Score links on latency, loss, bandwidth, cost, reliability | `links.py` | `test_utility_monotone_in_cost` |
| FR-5 | Hard limits for critical traffic (latency <= 100 ms, loss <= 1%, bandwidth >= 1 Mbps) | `links.py` | `test_satellite_excluded_from_critical_constraint` |
| FR-6 | Critical streams fail over after a short event-driven detection delay | `router.py` | `test_event_driven_failover_gap_is_detection_plus_switch` |
| FR-7 | Non-critical streams use timeout detection | `policies.py` | `test_timeout_detection_loses_more` |
| FR-8 | Return to the preferred link after a hold-down period | `router.py` | `test_event_driven_failover_gap_is_detection_plus_switch` |
| FR-9 | Ride out faults shorter than the detection delay | `router.py` | `test_fault_shorter_than_detection_is_ridden_out` |
| FR-10 | When no link is healthy, wait for the first recovery | `router.py` | `test_all_candidates_down_waits_for_first_recovery` |
| FR-11 | Damped score-driven switching (margin and hold count) | `flapping.py` | `test_single_spike_is_ignored_when_damped` |

## 3. Non-functional requirements
| ID | Requirement | Evidence |
|----|-------------|----------|
| NFR-1 | Deterministic, seeded simulation | `test_scenario_is_seeded_and_ordered` |
| NFR-2 | Cost accounting checked by hand | `test_policy_cost_hand_check` |
| NFR-3 | 30-day, 100-seed study runs in seconds | `research/run_study.py` |

## 4. Data
No real link data. Scenarios are generated from assumed fault processes (section 6).

## 5. Verification
`python -m pytest -q` (24 tests). `python research/run_study.py` for the study.

## 6. Assumptions (all unverified)
- Links: Ethernet/microwave 8 ms, 200 Mbps, cost 3.0, availability 0.999; 5G 30 ms, 150 Mbps, cost 1.0,
  availability 0.98; satellite 550 ms, 20 Mbps, cost 8.0, availability 0.995 (`links.py`).
- Offered load: critical 0.1 Mbps, non-critical 2 Mbps.
- Faults: Poisson outages (mean between outages 20 / 2 / 5 days for Ethernet / 5G / satellite) and
  degradations with lognormal durations (`scenario.py`).
- Detection: event-driven 30 ms (link-layer signalling), monitoring window 1 s, timeout 3 s.
- Faults on different links are independent.
