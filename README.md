# adaptive-data-routing-og-telecom

Criticality-aware, multi-criteria data routing for heterogeneous telecom links (Ethernet,
5G, satellite) on oil and gas sites. Product behind the SPE Offshore Europe 2027 submission
"Adaptive Multi-Criteria Data Routing System for Heterogeneous Telecommunication Infrastructures in
Oil and Gas Fields".

**Maturity: TRL 4 on simulated fault scenarios only** (see [docs/TRL.md](docs/TRL.md)). No real link
data, no hardware test, and the claims of the submitted abstract (40% cost reduction, 99.97% uptime,
failover under 50 ms) were *not* reproduced as stated (see [docs/ARTICLE.md](docs/ARTICLE.md)).

## What is here
- `src/ogrouting/fuzzy_ahp.py` Fuzzy AHP (Buckley) weights with a consistency check
- `src/ogrouting/classifier.py` critical / non-critical stream classification
- `src/ogrouting/links.py` link model, utility scoring, hard limits for critical traffic
- `src/ogrouting/router.py` event-based failover simulation of one stream
- `src/ogrouting/policies.py` proposed system, two baselines, three ablations
- `src/ogrouting/scenario.py`, `flapping.py` fault scenarios and measurement-noise study
- `research/run_study.py` the study; `research/results.json` its output
- `tests/` 24 unit tests; `docs/` SRS, BRS, TRL, manuscript

## Run
```bash
pip install -e ".[dev]"
python -m pytest -q
python research/run_study.py --seeds 100 --days 30 --out research/results.json
```
Docs: [BRS](docs/BRS.md) · [SRS](docs/SRS.md) · [TRL](docs/TRL.md) · [Manuscript](docs/ARTICLE.md)
