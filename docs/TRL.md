# Technology readiness (evidence-based)

**Level: TRL 4 for the decision and failover logic, on simulated fault scenarios only.** TRL 5 is not claimed.

## Evidence
- 24 unit tests pass (Python 3.13); they check the Fuzzy AHP, scoring, failover timing on hand-built
  timelines, cost accounting and damping.
- `research/run_study.py` (100 seeds x 30 days, synthetic faults) gives the numbers in `docs/ARTICLE.md`.

## What the simulation does not show
- No real link, router, PLC or SCADA was involved. Failover time is the assumed detection delay plus
  switching time (30 + 5 ms), which is a parameter; whether hardware reaches it is untested.
- Cost reduction is a function of the assumed cost ratios (63% at the default, none when the 5G link
  costs two-thirds of the Ethernet link).
- The abstract's 99.97% uptime was not reproduced; with independent link faults all policies exceed 99.999%.
- Non-critical traffic switched more often with the proposed rule (about 5 per day) than with the
  baselines (0.1 to 0.3 per day), because it prefers the less reliable 5G link.

## Next steps toward TRL 5
Measure real link statistics on one platform, replace the assumed parameters, test failover on router
hardware with fault signalling, and run the controller beside the SCADA network in shadow mode.
