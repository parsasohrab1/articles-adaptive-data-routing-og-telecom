"""Fuzzy AHP (Buckley geometric-mean method) with triangular fuzzy numbers.

Criteria order is fixed by CRITERIA. A pairwise matrix holds triangular fuzzy numbers
(l, m, u) for 'row criterion is x times as important as column criterion'.
"""

from __future__ import annotations

import numpy as np

CRITERIA = ("latency", "loss", "bandwidth", "cost", "reliability")

# Linguistic scale (Saaty-style, triangular fuzzy numbers)
EQUAL = (1.0, 1.0, 1.0)
MODERATE = (2.0, 3.0, 4.0)
STRONG = (4.0, 5.0, 6.0)
VERY_STRONG = (6.0, 7.0, 8.0)

# Random index for the consistency ratio (n = 1..8)
_RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41}


def reciprocal(t: tuple[float, float, float]) -> tuple[float, float, float]:
    l, m, u = t
    return (1.0 / u, 1.0 / m, 1.0 / l)


def build_matrix(upper: dict[tuple[str, str], tuple[float, float, float]]) -> np.ndarray:
    """Return an (n, n, 3) array of triangular fuzzy numbers from the upper-triangle judgments.
    Pairs not given default to EQUAL."""
    n = len(CRITERIA)
    idx = {c: i for i, c in enumerate(CRITERIA)}
    mat = np.ones((n, n, 3))
    for (a, b), t in upper.items():
        i, j = idx[a], idx[b]
        mat[i, j] = t
        mat[j, i] = reciprocal(t)
    return mat


def fuzzy_weights(mat: np.ndarray) -> np.ndarray:
    """Buckley's method: fuzzy geometric mean of each row, fuzzy normalisation, centroid
    defuzzification, then crisp normalisation. Returns weights summing to 1."""
    n = mat.shape[0]
    r = np.prod(mat, axis=1) ** (1.0 / n)            # (n, 3) fuzzy geometric means
    tot = r.sum(axis=0)                               # (3,)
    # fuzzy weight = r_i (x) (tot_u, tot_m, tot_l)^-1  (component-wise on l, m, u)
    w = np.stack([r[:, 0] / tot[2], r[:, 1] / tot[1], r[:, 2] / tot[0]], axis=1)
    crisp = w.mean(axis=1)
    return crisp / crisp.sum()


def consistency_ratio(mat: np.ndarray) -> float:
    """Saaty consistency ratio of the matrix of modal values (m components)."""
    a = mat[:, :, 1]
    n = a.shape[0]
    if n <= 2:
        return 0.0
    lam = float(np.max(np.linalg.eigvals(a).real))
    ci = (lam - n) / (n - 1)
    return ci / _RI[n]


CRITICAL_JUDGMENTS = {
    ("reliability", "latency"): MODERATE, ("reliability", "loss"): MODERATE,
    ("reliability", "bandwidth"): STRONG, ("reliability", "cost"): VERY_STRONG,
    ("latency", "loss"): EQUAL, ("latency", "bandwidth"): STRONG, ("latency", "cost"): VERY_STRONG,
    ("loss", "bandwidth"): STRONG, ("loss", "cost"): VERY_STRONG,
    ("bandwidth", "cost"): MODERATE,
}
NONCRITICAL_JUDGMENTS = {
    ("cost", "reliability"): MODERATE, ("cost", "bandwidth"): MODERATE,
    ("cost", "loss"): STRONG, ("cost", "latency"): VERY_STRONG,
    ("reliability", "bandwidth"): EQUAL, ("reliability", "loss"): MODERATE,
    ("reliability", "latency"): STRONG, ("bandwidth", "loss"): MODERATE,
    ("bandwidth", "latency"): MODERATE, ("loss", "latency"): MODERATE,
}


def profile_weights(profile: str) -> dict[str, float]:
    judg = {"critical": CRITICAL_JUDGMENTS, "noncritical": NONCRITICAL_JUDGMENTS}[profile]
    mat = build_matrix(judg)
    cr = consistency_ratio(mat)
    if cr > 0.1:
        raise ValueError(f"inconsistent judgments for {profile}: CR={cr:.3f}")
    return dict(zip(CRITERIA, fuzzy_weights(mat).tolist(), strict=True))
