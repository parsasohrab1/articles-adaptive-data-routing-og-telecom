"""Fault scenario generation (synthetic; parameters are assumptions, see docs/SRS.md)."""

from __future__ import annotations

import bisect
from dataclasses import dataclass

import numpy as np

DAY = 86400.0


@dataclass(frozen=True)
class Episode:
    link: str
    kind: str          # "down" | "degraded"
    start: float       # seconds
    end: float
    loss: float        # fraction of packets lost while degraded (1.0 when down)


# per-link fault process: (mean time between outages s, median outage s,
#                          mean time between degradations s, median degradation s, loss range)
FAULT_PARAMS = {
    "ethernet": (20 * DAY, 1800.0, 10 * DAY, 600.0, (0.02, 0.10)),
    "5g": (2 * DAY, 300.0, 0.5 * DAY, 240.0, (0.05, 0.20)),
    "satellite": (5 * DAY, 180.0, 1 * DAY, 300.0, (0.05, 0.30)),
}


def generate_episodes(horizon_s: float, rng: np.random.Generator,
                      scale: float = 1.0) -> list[Episode]:
    """Poisson arrivals, lognormal durations. `scale` multiplies the fault rates."""
    eps: list[Episode] = []
    for link, (mtbo, med_o, mtbd, med_d, (lo, hi)) in FAULT_PARAMS.items():
        for kind, mt, med in (("down", mtbo, med_o), ("degraded", mtbd, med_d)):
            t = rng.exponential(mt / scale)
            while t < horizon_s:
                dur = float(rng.lognormal(np.log(med), 0.8))
                loss = 1.0 if kind == "down" else float(rng.uniform(lo, hi))
                eps.append(Episode(link, kind, t, min(t + dur, horizon_s), loss))
                t += dur + rng.exponential(mt / scale)
    eps.sort(key=lambda e: e.start)
    return eps


class Timeline:
    """Fast lookup of the state of each link at a time."""

    def __init__(self, episodes: list[Episode]):
        self.by_link: dict[str, list[Episode]] = {}
        for e in episodes:
            self.by_link.setdefault(e.link, []).append(e)
        self._starts = {k: [e.start for e in v] for k, v in self.by_link.items()}

    def active(self, link: str, t: float) -> Episode | None:
        """Worst active episode on `link` at time t (down beats degraded)."""
        eps = self.by_link.get(link, [])
        i = bisect.bisect_right(self._starts.get(link, []), t)
        worst = None
        for e in reversed(eps[max(0, i - 6):i]):      # episodes overlap rarely; scan a few
            if e.start <= t < e.end and (worst is None or e.loss > worst.loss):
                worst = e
        return worst

    def next_start(self, link: str, t: float) -> Episode | None:
        eps = self.by_link.get(link, [])
        i = bisect.bisect_left(self._starts.get(link, []), t)
        return eps[i] if i < len(eps) else None

    def ongoing_or_next(self, link: str, t: float) -> Episode | None:
        a = self.active(link, t)
        return a if a is not None else self.next_start(link, t)
