import numpy as np

from ogrouting.flapping import count_switches, flapping_study
from ogrouting.fuzzy_ahp import profile_weights


def test_count_switches_basic():
    util = np.array([[1.0, 0.0]] * 5 + [[0.0, 1.0]] * 5)
    assert count_switches(util, 0.0, 1) == 1
    assert count_switches(util, 0.0, 10) == 0           # hold longer than the change


def test_single_spike_is_ignored_when_damped():
    util = np.array([[1.0, 0.0]] * 20)
    util[10] = [0.0, 1.0]
    assert count_switches(util, 0.0, 1) == 2            # away and back
    assert count_switches(util, 0.05, 10) == 0


def test_damping_reduces_switching():
    r = flapping_study(profile_weights("noncritical"), seed=0, seconds=3000)
    assert r["damped"] <= r["undamped"]
