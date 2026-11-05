"""Adaptive routing of one stream over a fault timeline.

The simulation is event-based: a stream sits on a link; a fault episode on that link is noticed
after a detection delay (policy dependent); the stream is then moved to the best healthy link.
During the delay the stream loses `loss` of its packets (all of them when the link is down).
After the preferred link has been healthy for `restore_hold_s`, a make-before-break switch
back is made (counted as a switch, no loss).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .links import Link
from .scenario import Timeline


@dataclass(frozen=True)
class Policy:
    name: str
    critical_profile: str            # weight profile used for critical streams
    noncritical_profile: str         # weight profile used for non-critical streams
    detect_down_critical_s: float    # time to notice a down link (critical stream)
    detect_degraded_critical_s: float | None   # None: degradations are never noticed
    detect_down_noncritical_s: float
    detect_degraded_noncritical_s: float | None
    restore_hold_s: float = 30.0
    switch_time_s: float = 0.005


@dataclass
class StreamResult:
    horizon_s: float
    lost_s: float = 0.0              # loss-weighted time (packets lost = rate x lost_s)
    worst_gap_s: float = 0.0
    unavailable_s: float = 0.0       # time with the path down or a switch under way
    switches: int = 0
    failover_times_s: list[float] = field(default_factory=list)
    failover_down_s: list[float] = field(default_factory=list)   # link-down events only
    time_on: dict[str, float] = field(default_factory=dict)


def _healthy(tl: Timeline, link: str, t: float) -> bool:
    return tl.active(link, t) is None


def _restore_time(tl: Timeline, pref: str, t: float, hold: float) -> float:
    """Earliest time >= t at which `pref` has been fault-free for `hold` seconds."""
    s = t
    for _ in range(100000):
        a = tl.active(pref, s)
        if a is not None:
            s = a.end
            continue
        nxt = tl.next_start(pref, s)
        if nxt is None or nxt.start >= s + hold:
            return s + hold
        s = nxt.end
    return float("inf")


def simulate_stream(links: list[Link], ranking: list[Link], tl: Timeline, horizon_s: float,
                    det_down: float, det_degraded: float | None, restore_hold_s: float,
                    switch_time_s: float, constraint=None) -> StreamResult:
    """`ranking` is the preference order (best first). `constraint(link)` filters candidates
    (hard limits for critical traffic); if no candidate is healthy, any healthy link is used
    (last resort)."""
    res = StreamResult(horizon_s)
    res.time_on = {lk.name: 0.0 for lk in links}
    cand = [lk for lk in ranking if constraint is None or constraint(lk)] or list(ranking)
    order = cand + [x for x in ranking if x not in cand]
    pref = cand[0]
    cur = pref
    t = 0.0

    def pick(at: float, exclude: str) -> Link | None:
        for lk in order:
            if lk.name != exclude and _healthy(tl, lk.name, at):
                return lk
        return None

    for _ in range(200000):
        if t >= horizon_s:
            break
        ep = tl.ongoing_or_next(cur.name, t)
        if cur is not pref:
            back = _restore_time(tl, pref.name, t, restore_hold_s)
            if (ep is None or ep.start >= back) and back < horizon_s:
                res.time_on[cur.name] += back - t
                t, cur = back, pref
                res.switches += 1
                continue
        if ep is None or ep.start >= horizon_s:
            res.time_on[cur.name] += horizon_s - t
            break
        start = max(ep.start, t)
        res.time_on[cur.name] += start - t
        det = det_down if ep.kind == "down" else det_degraded
        dur = ep.end - start
        if det is None or dur <= det:
            res.lost_s += dur * ep.loss
            res.time_on[cur.name] += dur
            if ep.kind == "down":
                res.unavailable_s += dur
                res.worst_gap_s = max(res.worst_gap_s, dur)
            t = ep.end
            continue
        sw_at = start + det
        res.lost_s += det * ep.loss
        res.time_on[cur.name] += det
        new = pick(sw_at, cur.name)
        if new is not None:
            gap = det + switch_time_s
            res.lost_s += switch_time_s * ep.loss
            if ep.kind == "down":
                res.unavailable_s += gap
            res.worst_gap_s = max(res.worst_gap_s, gap)
            res.failover_times_s.append(gap)
            if ep.kind == "down":
                res.failover_down_s.append(gap)
            res.switches += 1
            cur, t = new, sw_at + switch_time_s
            continue
        # nothing healthy: wait until another link recovers or this one does
        wait_end, target = ep.end, None
        for lk in order:
            a = tl.active(lk.name, sw_at)
            if lk.name != cur.name and a is not None and a.end < wait_end:
                wait_end, target = a.end, lk
        res.lost_s += (wait_end - sw_at) * ep.loss
        res.time_on[cur.name] += wait_end - sw_at
        gap = wait_end - start + (switch_time_s if target else 0.0)
        if ep.kind == "down":
            res.unavailable_s += gap
        res.worst_gap_s = max(res.worst_gap_s, gap)
        if target is not None:
            res.switches += 1
            res.failover_times_s.append(gap)
            if ep.kind == "down":
                res.failover_down_s.append(gap)
            cur, t = target, wait_end + switch_time_s
        else:
            t = ep.end
    return res
