import numpy as np
import pytest

from ogrouting.links import DEFAULT_LINKS, feasible_for_critical, rank
from ogrouting.policies import POLICIES, run_policy
from ogrouting.router import simulate_stream
from ogrouting.scenario import Episode, Timeline, generate_episodes

H = 1000.0


def crit(tl, det_down=0.03, det_deg=1.0, hold=30.0):
    return simulate_stream(DEFAULT_LINKS, rank(DEFAULT_LINKS, "critical"), tl, H, det_down,
                           det_deg, hold, 0.005, feasible_for_critical)


def test_no_faults_no_switches():
    r = crit(Timeline([]))
    assert r.switches == 0 and r.lost_s == 0 and r.time_on["ethernet"] == H


def test_event_driven_failover_gap_is_detection_plus_switch():
    r = crit(Timeline([Episode("ethernet", "down", 100, 200, 1.0)]))
    assert r.failover_times_s == [pytest.approx(0.035)]
    assert r.lost_s == pytest.approx(0.035)
    assert r.switches == 2                                  # to 5g, then back after the hold
    assert r.time_on["5g"] == pytest.approx(200 + 30 - 100.035 + 0.0, abs=0.01)


def test_timeout_detection_loses_more():
    fast = crit(Timeline([Episode("ethernet", "down", 100, 200, 1.0)]))
    slow = crit(Timeline([Episode("ethernet", "down", 100, 200, 1.0)]), det_down=3.0)
    assert slow.lost_s == pytest.approx(3.005) and slow.lost_s > 50 * fast.lost_s


def test_fault_shorter_than_detection_is_ridden_out():
    r = crit(Timeline([Episode("ethernet", "down", 100, 100.01, 1.0)]))
    assert r.switches == 0 and r.lost_s == pytest.approx(0.01)


def test_all_candidates_down_waits_for_first_recovery():
    tl = Timeline([Episode("ethernet", "down", 100, 300, 1.0),
                   Episode("5g", "down", 90, 150, 1.0),
                   Episode("satellite", "down", 90, 400, 1.0)])
    r = crit(tl)
    assert r.worst_gap_s >= 50.0                            # waited for 5g to return at t=150
    assert r.unavailable_s < 200.0                          # better than waiting for ethernet


def test_degradation_loss_accrues_until_detected():
    r = crit(Timeline([Episode("ethernet", "degraded", 100, 200, 0.1)]), det_deg=1.0)
    assert r.lost_s == pytest.approx(0.1 * 1.0 + 0.1 * 0.005)
    none = crit(Timeline([Episode("ethernet", "degraded", 100, 200, 0.1)]), det_deg=None)
    assert none.lost_s == pytest.approx(10.0)


def test_scenario_is_seeded_and_ordered():
    a = generate_episodes(86400 * 10, np.random.default_rng(3))
    b = generate_episodes(86400 * 10, np.random.default_rng(3))
    assert a == b and all(a[i].start <= a[i + 1].start for i in range(len(a) - 1))


def test_policy_cost_hand_check():
    # no faults: critical stays on ethernet, non-critical on 5g for the proposed system
    out = run_policy("proposed", Timeline([]), 86400.0)
    expected = (0.1 / 8 * 3.0 + 2.0 / 8 * 1.0) * 86400.0
    assert out["cost_per_day"] == pytest.approx(expected)
    assert out["critical_availability"] == 1.0


def test_no_classification_costs_more_without_faults():
    tl = Timeline([])
    assert run_policy("no_classification", tl, 86400.0)["cost_per_day"] > \
        run_policy("proposed", tl, 86400.0)["cost_per_day"]


def test_all_policies_run():
    tl = Timeline(generate_episodes(86400 * 5, np.random.default_rng(1)))
    for name in POLICIES:
        out = run_policy(name, tl, 86400 * 5)
        assert 0.0 <= out["critical_availability"] <= 1.0
