# SETI silence audit

A reproducible research audit of what the UCLA 2020–2023 radio null says about physical arrival within the following 100 years, within a declared finite population and explicit observation models.

The [blueprint](docs/blueprint.md), [specification](docs/superpowers/specs/2026-11-02-seti-silence-audit-design.md), and [implementation plan](docs/superpowers/plans/2026-11-02-seti-silence-audit.md) define the experiment. Implementation is in progress; no empirical result is claimed yet.

Use native Python 3.12 or newer:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pytest -q
python -m seti_audit run-logged --stage G1 -- python -m pytest -q
```

`requirements.lock.txt` records verified dependency versions. Resource records and interrupted-job identities are retained under `results/`; accounting imposes no time or workload quota. Synthetic controls and measured survey evidence will remain explicitly identified throughout the audit.
