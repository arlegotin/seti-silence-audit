# SETI silence audit

A reproducible research audit of what the UCLA 2020–2023 radio null says about physical arrival within the following 100 years, within a declared finite population and explicit observation models.

The question is whether hearing no radio signals narrows the range of physical-arrival probabilities in the declared models. Radio silence and physical safety are different observations. Allowing an invisible counterpart of every model prevents full-family contraction; the conditional radio-bright comparison remains a separate numerical question.

The [blueprint](docs/blueprint.md), [specification](docs/superpowers/specs/2026-11-02-seti-silence-audit-design.md), and [implementation plan](docs/superpowers/plans/2026-11-02-seti-silence-audit.md) define the experiment. The computational pipeline is implemented; full research confirmation and review are still pending. No empirical arrival forecast is claimed.

Use native Python 3.12 or newer:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install -e . --no-deps
python -m seti_audit check
python -m seti_audit smoke --config config/protocol.json --out results/smoke
```

Python 3.12 on native ARM64 macOS is the verified environment. `requirements.lock.txt` pins the actual scientific dependencies. `check` runs the complete offline test suite and saves code/test hashes, package versions, output, and a readiness identifier. Selected development checks cannot certify research readiness. The smoke command uses a one-star synthetic history with linked visits and also exercises the tiny ideal/reference paths; its report is explicitly synthetic. Use a fresh smoke output directory after changing the scientific code, since frozen outputs are immutable.

The current input grade is verified published geometry, coarsened timing **F1**, and assumed detector response **F2**. All 62 published rows match the source table, with 61 physical sites after linking the repeated TOI 1730.01 visit. Public archive metadata are accessible, but the tested individual download routes return 401/403; the whole-dataset route reports that ZIP generation is unavailable for this dataset size. Saved evidence is under [inputs](inputs). Expected archive hashes remain metadata expectations until file bytes are verified. Candidate hits alone cannot prove scan completeness, including zero-hit scans.

Run these commands from the checkout root:

```bash
python -m seti_audit env --out results/environment.json
python -m seti_audit acquire --config config/protocol.json
python -m seti_audit validate-data --config config/protocol.json
python -m seti_audit theorem-check --config config/protocol.json
python -m seti_audit check
python -m seti_audit calibrate --config config/protocol.json
python -m seti_audit pilot --config config/protocol.json
python -m seti_audit freeze --config config/protocol.json
python -m seti_audit run --protocol results/protocol.lock.json
python -m seti_audit report --protocol results/protocol.lock.json --from-results
```

`acquire` streams available sources, records access/integrity failures, and establishes the attained data grade. It does not turn an arbitrary retry count into evidence of unavailability. F1 retains the permitted date intervals and both 150-second ON durations; it invents no scan timestamps. F2 probabilities are detector assumptions, including Dpositive's positive floor. They are not empirical calibration confidence limits.

`theorem-check` independently evaluates the finite-age formulas and the repaired warning expression from the supplied PDF. Its original computation scripts were not attached. `--shell --histories 1000 --phase development` runs a separate development shell check; frozen confirmation includes its own registered shell experiments. Agreement with that continuum reference does not establish its applicability to the stellar catalog.

`calibrate` measures actual clocks, propagation, selection, quadrature, replays, imports, memory, and serialization. Runtime projections guide execution; they never shrink the scientific matrix. `pilot` checks the prescribed development cases and exact positive/null/sign controls. `freeze` requires current complete correctness, calibration, and pilot evidence and binds the inputs, scientific grid, numerical policy, registry, dependencies, code, and seeds.

The matrix contains 16 primary demographics, four age diagnostics, and 16 same-star ideal settings with paired continuation replays. Future k=0/10 controls cover E1/E0; age diagnostics use E1 and the three point detectors. It is a one-factor robustness design. The source theorem, finite independent-site model, interacting model, and perfect-silence comparator retain their different conditioning and interpretation.

For an interrupted run:

```bash
python -m seti_audit run --protocol results/protocol.lock.json --resume
```

Valid published orphan batches are recovered by hash. Committed counts and seed identities are never duplicated, reset, or discarded. Logical batches have fixed seed streams; memory-sized propagation can use the same clocks. Resume rejects changed inputs, dependencies, code identity, corrupted aggregates, and simultaneous writers. The local checkpoint store is ignored by git and is required to continue that run. Saved aggregate evidence is sufficient to regenerate its report without raw trajectories or archive downloads.

Initial sample sizes are planning checkpoints: 100,000 primary survivors, 25,000 per age/ideal setting, 50,000 mixed-speed proposals, and 10,000 shell histories. Required precision extends through cumulative doubling checkpoints. Each unique interval uses `alpha=A/(M*j*(j+1))`, with .025 for primary decisions and .025 for diagnostics; thresholds reuse intervals. There is no maximum look, project duration, byte quota, launch allowance, repair allowance, or reporting-cell quota. Actual RAM/storage constraints trigger smaller physical work units or a resumable interruption.

An explicit further precision look also preserves the frozen experiment:

```bash
python -m seti_audit run --protocol results/protocol.lock.json --resume --extend
```

Reports consume saved evidence in both forms:

```bash
python -m seti_audit report --protocol results/protocol.lock.json
python -m seti_audit report --protocol results/protocol.lock.json --from-results
```

They produce `report/REPORT.md`, exportable figures, `results/model_rows.json`, CSV tables, family envelopes, evidence paths/hashes, and scoped `conclusions.json`. Missing cells remain unresolved outer-envelope contributors. An excluded family has no conditional risk, not zero risk. Undefined points use null/status fields. Weighted estimates, Monte Carlo intervals, quadrature error, and nuisance bounds remain distinct. All five outcome categories apply per claim; an unfinished calculation remains pending.

Independently resolved or blocked components can be reported before a numerical experiment is frozen:

```bash
python -m seti_audit report --evidence results/evidence_status.json --from-results
```

That saved record must identify its `pre_freeze` stage, scoped claims, prerequisites, and evidence paths/hashes. This path creates no protocol lock or numerical confirmation.

Operational records are append-only under `results/`. Durations include nested checks when summed and therefore are not unique wall time. Failed and exploratory work remains in the ledger. `run-logged --stage G1 -- <command>` records additional computational checks. CLI exit codes are 0 for the attained stage, 2 for invalid configuration/lock, 3 for blocking input, 4 for invalid correctness, and 5 for an actual resource interruption with resumable work.
