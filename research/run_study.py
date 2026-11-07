"""Simulation study: proposed routing vs baselines and ablations (synthetic scenarios only).

Usage: python research/run_study.py --seeds 100 --days 30 --out research/results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ogrouting.flapping import flapping_study
from ogrouting.fuzzy_ahp import profile_weights
from ogrouting.links import DEFAULT_LINKS
from ogrouting.policies import POLICIES, run_policy
from ogrouting.scenario import DAY, Timeline, generate_episodes

KEYS = ["critical_availability", "critical_loss_fraction", "critical_worst_gap_s",
        "critical_failover_s", "critical_failover_down_s", "critical_switches_per_day", "noncritical_unserved_fraction",
        "noncritical_switches_per_day", "cost_per_day"]


def ci(x: np.ndarray, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    m = [float(np.mean(x[rng.integers(0, len(x), len(x))])) for _ in range(2000)]
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def summarise(rows: list[dict]) -> dict:
    out = {}
    for k in KEYS:
        v = np.array([r[k] for r in rows if r[k] is not None], dtype=float)
        out[k] = {"mean": float(v.mean()), "ci95": ci(v), "max": float(v.max()), "n": len(v)}
    return out


def run(seeds: int, days: float, scale: float = 1.0, event_detect_s: float | None = None) -> dict:
    H = days * DAY
    per = {p: [] for p in POLICIES}
    for s in range(seeds):
        tl = Timeline(generate_episodes(H, np.random.default_rng(1000 + s), scale))
        for p in POLICIES:
            per[p].append(run_policy(p, tl, H, event_detect_s=event_detect_s))
    return {p: summarise(r) for p, r in per.items()}, per


def paired_cost_reduction(per: dict, base: str, other: str = "proposed") -> dict:
    a = np.array([r["cost_per_day"] for r in per[base]])
    b = np.array([r["cost_per_day"] for r in per[other]])
    red = (a - b) / a * 100.0
    return {"mean_pct": float(red.mean()), "ci95": ci(red)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--days", type=float, default=30)
    ap.add_argument("--flap-seeds", type=int, default=10)
    ap.add_argument("--out", default="research/results.json")
    a = ap.parse_args()
    main_res, per = run(a.seeds, a.days)
    res = {"assumptions": "synthetic fault scenarios; see docs/SRS.md section 6",
           "seeds": a.seeds, "days": a.days, "policies": main_res,
           "cost_reduction_vs": {b: paired_cost_reduction(per, b) for b in POLICIES if b != "proposed"},
           "sensitivity": {}}
    for scale in (0.5, 2.0, 4.0):
        r, _ = run(max(20, a.seeds // 4), a.days, scale=scale)
        res["sensitivity"][f"fault_rate_x{scale}"] = {
            q: {k: r[q][k]["mean"] for k in ("critical_availability", "critical_loss_fraction",
                                              "cost_per_day")} for q in ("proposed", "static_primary_backup", "qos_only")}
    for d in (0.01, 0.2, 1.0):
        r, _ = run(max(20, a.seeds // 4), a.days, event_detect_s=d)
        res["sensitivity"][f"event_detect_{d}s"] = {
            "proposed": {k: r["proposed"][k]["mean"] for k in ("critical_availability",
                                                               "critical_loss_fraction")}}
    res["cost_reduction_vs_5g_cost"] = {}
    for c5 in (0.5, 1.0, 2.0, 3.0, 4.0):
        links = [replace(lk, cost_per_mb=c5) if lk.name == "5g" else lk for lk in DEFAULT_LINKS]
        pr = {q: [] for q in ("proposed", "qos_only")}
        for sd in range(20):
            tl = Timeline(generate_episodes(a.days * DAY, np.random.default_rng(5000 + sd)))
            for q in pr:
                pr[q].append(run_policy(q, tl, a.days * DAY, links=links))
        red = [(x["cost_per_day"] - y["cost_per_day"]) / x["cost_per_day"] * 100
               for x, y in zip(pr["qos_only"], pr["proposed"], strict=True)]
        res["cost_reduction_vs_5g_cost"][str(c5)] = float(np.mean(red))
    fl = [flapping_study(profile_weights("noncritical"), seed=s) for s in range(a.flap_seeds)]
    res["steady_state_switches_per_day"] = {
        "undamped_mean": float(np.mean([f["undamped"] for f in fl])),
        "damped_mean": float(np.mean([f["damped"] for f in fl])), "seeds": a.flap_seeds}
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
