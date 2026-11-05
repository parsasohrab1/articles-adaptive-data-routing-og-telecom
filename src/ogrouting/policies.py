"""Routing policies: the proposed system, two baselines and three ablations."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .fuzzy_ahp import profile_weights
from .links import DEFAULT_LINKS, Link, feasible_for_critical, rank
from .router import Policy, StreamResult, simulate_stream
from .scenario import Timeline

CRIT_RATE_MBPS, NONCRIT_RATE_MBPS = 0.1, 2.0     # offered load (assumed)
EVENT_DETECT_S = 0.03                            # link-layer fault signalling, e.g. 3 x 10 ms BFD
TIMEOUT_S = 3.0                                  # routing dead-timer style detection
MONITOR_S = 1.0                                  # monitoring window for degradations

QOS_ONLY_WEIGHTS = {"latency": 0.30, "loss": 0.25, "bandwidth": 0.15, "cost": 0.0,
                    "reliability": 0.30}

POLICIES: dict[str, Policy] = {
    "proposed": Policy("proposed", "critical", "noncritical", EVENT_DETECT_S, MONITOR_S, 5.0, 30.0),
    "static_primary_backup": Policy("static_primary_backup", "static", "static",
                                    TIMEOUT_S, None, TIMEOUT_S, None),
    "qos_only": Policy("qos_only", "qos", "qos", MONITOR_S, MONITOR_S, MONITOR_S, MONITOR_S),
    "no_classification": Policy("no_classification", "critical", "critical",
                                EVENT_DETECT_S, MONITOR_S, EVENT_DETECT_S, MONITOR_S),
    "timeout_only_critical": Policy("timeout_only_critical", "critical", "noncritical",
                                    TIMEOUT_S, MONITOR_S, 5.0, 30.0),
    "no_cost_factor": Policy("no_cost_factor", "critical", "critical",
                             EVENT_DETECT_S, MONITOR_S, 5.0, 30.0),
}
STATIC_ORDER = ["ethernet", "5g", "satellite"]
CLASSIFYING = {"proposed", "timeout_only_critical", "no_classification", "no_cost_factor"}


def ranking_for(profile: str, links: list[Link]) -> list[Link]:
    if profile == "static":
        by = {lk.name: lk for lk in links}
        return [by[n] for n in STATIC_ORDER if n in by]
    if profile == "qos":
        return rank(links, "qos", QOS_ONLY_WEIGHTS)
    return rank(links, profile, profile_weights(profile))


def run_policy(name: str, tl: Timeline, horizon_s: float,
               links: list[Link] | None = None, event_detect_s: float | None = None) -> dict:
    links = links or DEFAULT_LINKS
    pol = POLICIES[name]
    if event_detect_s is not None and name in ("proposed", "no_classification", "no_cost_factor"):
        pol = replace(pol, detect_down_critical_s=event_detect_s,
                      detect_down_noncritical_s=pol.detect_down_noncritical_s
                      if name != "no_classification" else event_detect_s)
    cons = feasible_for_critical if name in CLASSIFYING else None
    crit = simulate_stream(links, ranking_for(pol.critical_profile, links), tl, horizon_s,
                           pol.detect_down_critical_s, pol.detect_degraded_critical_s,
                           pol.restore_hold_s, pol.switch_time_s, cons)
    nonc = simulate_stream(links, ranking_for(pol.noncritical_profile, links), tl, horizon_s,
                           pol.detect_down_noncritical_s, pol.detect_degraded_noncritical_s,
                           pol.restore_hold_s, pol.switch_time_s, None)
    cost = {lk.name: lk.cost_per_mb for lk in links}

    def mb_cost(res: StreamResult, rate: float) -> float:
        return sum(res.time_on[n] * rate / 8.0 * cost[n] for n in res.time_on)

    days = horizon_s / 86400.0
    c_cost, n_cost = mb_cost(crit, CRIT_RATE_MBPS), mb_cost(nonc, NONCRIT_RATE_MBPS)
    return {
        "critical_availability": 1.0 - crit.unavailable_s / horizon_s,
        "critical_loss_fraction": crit.lost_s / horizon_s,
        "critical_worst_gap_s": crit.worst_gap_s,
        "critical_failover_s": float(np.mean(crit.failover_times_s)) if crit.failover_times_s else None,
        "critical_failover_down_s": (float(np.mean(crit.failover_down_s))
                                     if crit.failover_down_s else None),
        "critical_switches_per_day": crit.switches / days,
        "noncritical_unserved_fraction": nonc.unavailable_s / horizon_s,
        "noncritical_switches_per_day": nonc.switches / days,
        "cost_per_day": (c_cost + n_cost) / days,
        "cost_noncritical_per_day": n_cost / days,
        "noncritical_share_on": {k: v / horizon_s for k, v in nonc.time_on.items()},
    }
