"""Link model and utility scoring."""

from __future__ import annotations

from dataclasses import dataclass

from .fuzzy_ahp import profile_weights


@dataclass(frozen=True)
class Link:
    name: str
    kind: str                 # "ethernet" | "5g" | "satellite"
    latency_ms: float         # nominal one-way latency
    bandwidth_mbps: float
    loss_pct: float           # nominal loss
    cost_per_mb: float        # relative cost units
    reliability: float        # long-run availability in [0, 1]


# Reference scales for the benefit transforms (documented assumptions, see docs/SRS.md)
REF_LAT_MS, REF_LOSS_PCT, REF_BW_MBPS, REF_COST = 50.0, 0.5, 50.0, 2.0


def criterion_scores(link: Link) -> dict[str, float]:
    """Map each criterion to (0, 1], higher is better."""
    return {
        "latency": REF_LAT_MS / (REF_LAT_MS + link.latency_ms),
        "loss": 1.0 / (1.0 + link.loss_pct / REF_LOSS_PCT),
        "bandwidth": link.bandwidth_mbps / (link.bandwidth_mbps + REF_BW_MBPS),
        "cost": REF_COST / (REF_COST + link.cost_per_mb),
        "reliability": link.reliability,
    }


def utility(link: Link, weights: dict[str, float]) -> float:
    s = criterion_scores(link)
    return sum(weights[c] * s[c] for c in weights)


def rank(links: list[Link], profile: str, weights: dict[str, float] | None = None) -> list[Link]:
    w = weights or profile_weights(profile)
    return sorted(links, key=lambda lk: -utility(lk, w))


# Hard constraints for critical traffic (control commands, safety alarms)
CRIT_MAX_LATENCY_MS, CRIT_MAX_LOSS_PCT, CRIT_MIN_BW_MBPS = 100.0, 1.0, 1.0


def feasible_for_critical(link: Link) -> bool:
    return (link.latency_ms <= CRIT_MAX_LATENCY_MS and link.loss_pct <= CRIT_MAX_LOSS_PCT
            and link.bandwidth_mbps >= CRIT_MIN_BW_MBPS)


# Representative offshore platform link set (assumed values; replace with measured ones)
DEFAULT_LINKS = [
    Link("ethernet", "ethernet", 8.0, 200.0, 0.01, 3.0, 0.999),
    Link("5g", "5g", 30.0, 150.0, 0.2, 1.0, 0.98),
    Link("satellite", "satellite", 550.0, 20.0, 0.5, 8.0, 0.995),
]
