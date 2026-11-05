"""Stream criticality classification (critical vs non-critical)."""

from __future__ import annotations

from dataclasses import dataclass

CRITICAL_TAGS = {"plc_command", "safety_alarm", "esd", "pressure", "temperature", "flow"}
NONCRITICAL_TAGS = {"video", "historian_bulk", "log", "software_update", "voip", "backup"}


@dataclass(frozen=True)
class Stream:
    name: str
    tag: str
    rate_mbps: float


def classify(stream: Stream) -> str:
    """Return 'critical' or 'noncritical'. Unknown tags are treated as critical (fail safe)."""
    if stream.tag in NONCRITICAL_TAGS:
        return "noncritical"
    return "critical"
