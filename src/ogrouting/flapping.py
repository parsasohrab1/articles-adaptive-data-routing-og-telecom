"""Steady-state switching under measurement noise (no real faults).

Compares score-driven re-selection without damping (the QoS-only baseline) with the proposed
rule: switch only when another link beats the current one by `margin` for `hold` consecutive
measurements. Critical streams never switch on scores in steady state (event-driven only).
"""

from __future__ import annotations

import numpy as np

from .links import DEFAULT_LINKS, Link, criterion_scores


def _measured_utility(links: list[Link], weights: dict[str, float], rng: np.random.Generator,
                      n: int, spike_prob: float) -> np.ndarray:
    out = np.zeros((n, len(links)))
    for j, lk in enumerate(links):
        lat = lk.latency_ms * rng.lognormal(0.0, 0.25, n)
        spikes = rng.random(n) < spike_prob
        lat = np.where(spikes, lat * rng.uniform(2.0, 5.0, n), lat)
        loss = rng.binomial(100, lk.loss_pct / 100.0, n) / 100.0 * 100.0      # % over 100 probes
        bw = lk.bandwidth_mbps * rng.uniform(0.6, 1.0, n)
        s = np.zeros(n)
        for i in range(n):
            m = Link(lk.name, lk.kind, float(lat[i]), float(bw[i]), float(loss[i]),
                     lk.cost_per_mb, lk.reliability)
            sc = criterion_scores(m)
            s[i] = sum(weights[c] * sc[c] for c in weights)
        out[:, j] = s
    return out


def count_switches(util: np.ndarray, margin: float, hold: int) -> int:
    """Number of changes of the selected link."""
    cur = int(np.argmax(util[0]))
    switches, streak, cand = 0, 0, None
    for row in util[1:]:
        best = int(np.argmax(row))
        if best != cur and row[best] > row[cur] + margin:
            streak = streak + 1 if cand == best else 1
            cand = best
            if streak >= hold:
                cur, streak, cand = best, 0, None
                switches += 1
        else:
            streak, cand = 0, None
    return switches


def flapping_study(weights: dict[str, float], seed: int, seconds: int = 86400,
                   spike_prob: float = 0.01, links: list[Link] | None = None) -> dict:
    links = links or DEFAULT_LINKS
    rng = np.random.default_rng(seed)
    util = _measured_utility(links, weights, rng, seconds, spike_prob)
    return {"undamped": count_switches(util, 0.0, 1), "damped": count_switches(util, 0.05, 10)}
