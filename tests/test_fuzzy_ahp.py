import numpy as np
import pytest

from ogrouting.fuzzy_ahp import (
    CRITERIA,
    EQUAL,
    MODERATE,
    build_matrix,
    consistency_ratio,
    fuzzy_weights,
    profile_weights,
    reciprocal,
)


def test_reciprocal_swaps_bounds():
    assert reciprocal((2.0, 3.0, 4.0)) == (0.25, 1 / 3, 0.5)


def test_equal_judgments_give_equal_weights():
    w = fuzzy_weights(build_matrix({}))
    assert np.allclose(w, 1 / len(CRITERIA))


def test_weights_sum_to_one_and_follow_judgment():
    w = fuzzy_weights(build_matrix({("cost", "latency"): MODERATE}))
    d = dict(zip(CRITERIA, w, strict=True))
    assert abs(sum(w) - 1.0) < 1e-12
    assert d["cost"] > d["latency"]


@pytest.mark.parametrize("profile", ["critical", "noncritical"])
def test_profiles_are_consistent_and_normalised(profile):
    w = profile_weights(profile)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert set(w) == set(CRITERIA)


def test_profile_priorities():
    c, n = profile_weights("critical"), profile_weights("noncritical")
    assert max(c, key=c.get) == "reliability"
    assert max(n, key=n.get) == "cost"
    assert c["cost"] < n["cost"] and c["latency"] > n["latency"]


def test_inconsistent_matrix_has_high_cr():
    # a > b > c > a  (cyclic judgments)
    mat = build_matrix({("latency", "loss"): MODERATE, ("loss", "bandwidth"): MODERATE,
                        ("bandwidth", "latency"): MODERATE, ("cost", "reliability"): EQUAL})
    assert consistency_ratio(mat) > 0.1
