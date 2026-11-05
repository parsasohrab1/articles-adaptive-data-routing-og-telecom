from ogrouting.classifier import Stream, classify
from ogrouting.fuzzy_ahp import profile_weights
from ogrouting.links import DEFAULT_LINKS, feasible_for_critical, rank, utility


def test_classification():
    assert classify(Stream("esd", "esd", 0.01)) == "critical"
    assert classify(Stream("cctv", "video", 4.0)) == "noncritical"
    assert classify(Stream("mystery", "unknown_tag", 0.1)) == "critical"      # fail safe


def test_ranking_by_profile():
    assert rank(DEFAULT_LINKS, "critical")[0].name == "ethernet"
    assert rank(DEFAULT_LINKS, "noncritical")[0].name == "5g"


def test_satellite_excluded_from_critical_constraint():
    names = [lk.name for lk in DEFAULT_LINKS if feasible_for_critical(lk)]
    assert names == ["ethernet", "5g"]


def test_utility_monotone_in_cost():
    w = profile_weights("noncritical")
    cheap = DEFAULT_LINKS[1]
    dear = type(cheap)(cheap.name, cheap.kind, cheap.latency_ms, cheap.bandwidth_mbps,
                       cheap.loss_pct, cheap.cost_per_mb * 3, cheap.reliability)
    assert utility(cheap, w) > utility(dear, w)
