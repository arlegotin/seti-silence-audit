# SETI Silence Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible, uncertainty-qualified finite-target audit of how the UCLA radio null changes century-arrival probability envelopes, or a justified result at an earlier evidence gate.

**Architecture:** One Python package shares demographic histories across emission/detector variants. A scalar suppression engine, exact conditional sampler, linked likelihood, deterministic independent oracle, and separate continuum reference feed a frozen experiment matrix and aggregate-only reporting. Build and validate the mathematical controls before the full runner; acquisition/calibration failures select the declared evidence grade rather than fabricated inputs.

**Tech Stack:** Python 3.12 or newer; NumPy, SciPy, Matplotlib, pytest, mpmath; standard-library argparse, dataclasses, CSV/JSON, urllib, hashlib, pathlib, datetime, and atomic filesystem writes. Verify and lock successful versions on the actual machine.

**Spec:** [Approved research and software specification](../specs/2026-11-02-seti-silence-audit-design.md). Read it alongside [the normative blueprint](../../blueprint.md) and [the mathematical reference](../../silence_contact_theorem.pdf). No package, tests, or CLI exists yet; commands below are implementation targets.

## Global Constraints

- Use CPU binary64; no MPS/float32 substitution, cloud compute, CUDA, or paid services.
- Local experimental compute and result generation: 6 wall-clock hours, including tests, failed runs, compilation, repairs, and optional acceleration; sum concurrent job durations.
- Network/data acquisition: 60 minutes elapsed and 5.0 GB downloaded, including metadata and ordinary source documents.
- Peak process RSS: `min(8 GiB,0.25*physical RAM)`; total project disk: 8 GiB with at least 4 GiB free beyond the planned footprint; generated results/checkpoints: 1 GiB.
- Candidate universes/history evaluations: 60 million globally; mixed-speed demographic setting: 12 million attempts, also subject to the global cap; charge diagnostics and future replays.
- Survivor targets: 100,000 primary, cost-only fallback 25,000; age diagnostics 25,000 each; ideal silence 25,000 per primary demographic; shell references 20,000 total.
- At most 30 development/calibration/pilot launches; 20 interacting plus 16 ideal-silence confirmatory ensembles; at most 2,000 pre-enumerated reporting cells.
- Repair allowance: 30 minutes compute, at most two targeted repairs per failed gate, included in the 6 hours; reserve the last 35 minutes for reporting.
- Development seeds: `SeedSequence([20261101,0,...])`; confirmation seeds: `SeedSequence([20261101,1,...])`; stable integer IDs, recorded generator and NumPy version.
- Scientific grid, effect thresholds, sample-size choice, error allocation, data hashes/grades, attempt caps, seeds, tolerances, and stopping rules are immutable after protocol freeze; a scientific deviation needs a dated entry and fresh evidence within the remaining budget or is exploratory.

Continue on the user's current branch, `main`; do not create a worktree or switch branches. Preserve both original source hashes. Use the matrix, grades, inequalities, and numerical tolerances in spec §§3–8 exactly. Dnom/Dweak/Dhigh are assumptions, not calibrated confidence limits. Keep fully invisible counterparts analytic. Scope is implementation and research execution only when subsequently authorized; this planning delivery runs no experiments.

## Review Focus

1. **A crash between reservation, batch write, and checkpoint:** resumed work must not duplicate evidence or reset spent resources; Task 12 fault injection.
2. **A source absent from candidate rows or a truncated final CSV:** plausible timestamps must not certify a complete schedule; Tasks 2–3 completeness and interrupted-stream tests.
3. **Boundary ties, negative-zero coordinates, and endpoint uniforms:** preserve exact event inequalities, geometry signs, and subluminal support; Tasks 2, 4, and 8 deterministic controls.
4. **No null draws, an empty retained family, or a cap-interrupted high-risk cell:** retain uncertainty and distinguish incompatibility from zero risk; Task 10 decision tests.
5. **Repeated observations with a shared source status and partially illuminated scans:** never redraw compatibility, infer independent visits, or apply full-ON calibration to a partial signal; Task 6 linked and bounded tests.

---

## File structure and execution conventions

| Planned file(s) | Responsibility / owning task |
|---|---|
| `pyproject.toml`, `README.md`, `requirements.lock.txt`, `.gitignore` | Package/setup; Task 1, completed in Task 13 |
| `config/protocol.json` | All scientific defaults, budgets, stage allocations; Task 1 |
| `src/seti_audit/contracts.py` | Shared dataclasses and validated schemas, extended by the task introducing each type |
| `src/seti_audit/budget.py`, `artifacts.py` | Resource accounting and atomic artifacts; Task 1, checkpoint behavior Task 12 |
| `src/seti_audit/data.py` | Catalog/schedule, Task 2; acquisition, Task 3 |
| `src/seti_audit/model.py` | Scalar process, Task 4; proposal/replay, Task 5; batching, Task 11 |
| `src/seti_audit/detection.py` | Linked likelihood and bounds; Task 6 |
| `src/seti_audit/oracles.py` | Independent and same-star ideal controls; Task 7 |
| `src/seti_audit/theorem.py` | Stable formulas, Task 8; finite shell, Task 9 |
| `src/seti_audit/inference.py` | Estimates, intervals, envelopes, certification; Task 10 |
| `src/seti_audit/experiments.py` | Calibration/pilot, Task 11; matrix/freeze/runner, Task 12 |
| `src/seti_audit/reporting.py` | Evidence tables, figures, claim statuses; Task 13 |
| `src/seti_audit/cli.py`, `__init__.py`, `__main__.py` | Thin dispatch; Task 1, extended by command owners |
| `tests/conftest.py`, `tests/test_*.py`, `tests/fixtures/*` | Offline correctness oracles and synthetic fixtures; corresponding task |
| `inputs/`, `data/`, `results/`, `report/` | Runtime artifacts specified below; commit small reproducibility artifacts deliberately, not bulk CSVs |

`FloatArray` means `numpy.typing.NDArray[numpy.float64]`; `IntArray` means `NDArray[numpy.int64]`. Public dataclasses live in `contracts.py`; implementation helpers stay private. Add fields only when consumed by a named task. Use `Path` paths, `numpy.random.Generator` RNG arguments, and JSON-safe artifact representations. No NaN/infinity in JSON: use null plus an explicit censoring/status field.

Tests use tiny offline fixtures, not archive downloads or full confirmation. Run a red test before implementing its behavior and the named suite afterward. After Task 1, wrap local computational checks as `python -m seti_audit budget-run --stage G1 -- python -m pytest <paths> -q`; the wrapper records actual elapsed cost without counting nested work twice. Use the appropriate gate for later calibration/pilot/confirmation. Until this wrapper exists, record bootstrap test elapsed times in `results/bootstrap-cost.jsonl` and import them into the ledger once. Test budgets and temp artifacts use isolated fixtures; actual test runtime still counts globally. Commit checkpoints below are separate meaningful commits on `main`.

## Task 1: Create a package that enforces budgets and artifact integrity

**Files:** Create `pyproject.toml`, `config/protocol.json`, `src/seti_audit/{__init__,__main__,cli,contracts,budget,artifacts}.py`, `tests/conftest.py`, `tests/test_budget.py`, `tests/test_artifacts.py`, `tests/test_protocol.py`, initial `README.md`; modify `.gitignore`; generate `requirements.lock.txt` only after successful imports.

**Interfaces:**

- `load_protocol(path: Path) -> Protocol`; typed `Protocol` owns model/emission/detector lists, thresholds, seed roots, budget limits, stage allocations, and numerical tolerances from spec §§3–8. `ModelConfig(model_id:int,mu:float,age_years:float,speed_id:str,future_multiplier:float)`, `EmissionConfig(emission_id:str,zeta:float,delay_years:float,lifetime_years:float|None,activity:str)`, and `DetectorConfig(detector_id:str,pair_low:float,pair_high:float,allow_partial:bool)` are shared contracts. E5's fixed CTMC constants live in emission configuration.
- `BudgetLedger(path: Path, limits: BudgetLimits)`: `reserve(stage:str,seconds:float,histories:int,download_bytes:int=0,ensemble_id:int|None=None) -> str`; `finish(reservation_id:str,actual_seconds:float,actual_histories:int,actual_bytes:int=0) -> None`. Refuse new work beyond caps/report reserve; persist a pending lease before launch and reconcile interrupted leases conservatively.
- `canonical_hash(value: object) -> str`, `write_json_atomic(path: Path,value: object) -> str`, `read_json_checked(path: Path,expected_hash:str|None=None) -> dict`. Canonical JSON uses sorted keys, UTF-8, finite values, and a recorded schema version.
- `main(argv: list[str]|None=None) -> int`; provide `budget-run --stage <gate> -- <command>` and package dispatch now. Add scientific subcommands in their owning tasks.

- [ ] **Step 1: Write failing contract tests.** `test_budget_preserves_report_reserve` asserts 325 minutes used blocks another simulation but permits the 35-minute report; `test_reservation_survives_crash` asserts a pending lease does not restore capacity; `test_hash_round_trip` asserts canonical hashes survive key order changes; `test_reject_nonfinite_json` asserts NaN/inf fail. `test_protocol_exact_grid` asserts `mu==[.1,1,3,12]`, all S1–S4/E0–E5/detector IDs, 16 primary and four age configurations, thresholds `[.01,.05,.10]`, allocation sum `360`, and both source hashes. Assert bootstrap ledger entries import once.
- [ ] **Step 2: Run `python -m pytest tests/test_budget.py tests/test_artifacts.py tests/test_protocol.py -q`.** Expect missing package/contracts first; after package discovery exists, confirm assertions fail for the intended behavior. Record bootstrap duration.
- [ ] **Step 3: Implement the contracts, ledger, atomic JSON, and minimal CLI.** Use an installable `src` package, Python `>=3.12`, and the five required dependencies. Serialize reservations append-only and lock writers; reject concurrent mutation rather than race. Enforce both consumed and reserved capacity, network bytes, repair counts, proposal/evaluation caps, and reserved reporting time; monitor elapsed time/RSS/disk during jobs and stop before a hard cap, preserving failure evidence. Ignore `.venv/`, caches, bulk downloads, and machine-specific generated files without hiding explicitly retained evidence.
- [ ] **Step 4: Install locally and run the three suites through `budget-run`.** Expected: PASS, ledger reflects bootstrap plus verification once; `python -m seti_audit --help` exits 0. Verify imports, installed SciPy exact-binomial API, and `python -m pip freeze > requirements.lock.txt`; do not claim a supported environment if installation/import fails.
- [ ] **Step 5: Commit.** `git add pyproject.toml config src tests README.md requirements.lock.txt .gitignore`; `git commit -m "feat: add budgeted reproducible audit package"`.

## Task 2: Normalize the physical catalog and graded schedules

**Files:** Create `src/seti_audit/data.py`, `tests/test_data.py`, `tests/fixtures/schedule_cases.json`; extend `contracts.py`; produce `data/source_rows.csv`, `data/targets.csv`, `data/provenance.json` from local sources when validated.

**Interfaces:**

- `Geometry(site_ids:tuple[str,...],xyz_ly:FloatArray,radii_ly:FloatArray,distances_ly:FloatArray)`; `Catalog(source_rows:tuple[dict,...],geometry:Geometry,provenance:dict)`.
- `Scan(visit_id:str,site_id:str,scan_index:int,start_year:float,duration_year:float,paired_visit_id:str)`; `BoundedVisit(visit_id:str,site_id:str,allowed_intervals:tuple[tuple[float,float],...],duration_year:float)`; `Schedule(exact_scans:tuple[Scan,...],bounded_visits:tuple[BoundedVisit,...],schedule_grade:str,detector_grade:str,endpoint:dict,provenance:dict)`. Validate one representation per schedule. Interval windows and durations use observer time relative to zero.
- `load_catalog(blueprint_path:Path,output_dir:Path) -> Catalog`; `load_schedule(catalog:Catalog,input_dir:Path,output_dir:Path) -> Schedule`; `validate_schedule(schedule:Schedule,catalog:Catalog,completeness:dict) -> dict`. Exact grade requires a source-backed completeness record, never a self-asserted flag.

- [ ] **Step 1: Write failing geometry/grade tests.** Assert 62 rows become 61 sites; TOI 1730.01 has two linked visit rows; signed `-00:40:22.03` gives negative z; nearest radius is approximately `30.7891621` ly; precisely six unique sites have `r<100`. Assert contradictory duplicate geometry is rejected, all distance diagonals equal zero, and the matrix is symmetric. For two exact scans without completeness evidence, assert grade is not `exact`. F1 assertions: two allowed date components for each group, endpoint May 13–15 2023 UTC, 150-second durations, and no fabricated exact timestamps.
- [ ] **Step 2: Run `tests/test_data.py` through the budget wrapper.** Expected: FAIL for absent catalog/schedule behavior.
- [ ] **Step 3: Implement parsing and schedule validation.** Retain string identifiers and all original row provenance; use the spec's exact parsec conversion and 3D formula. Implement interval subtraction/union with no arbitrary date imputation. Exact schedule validation checks two nonoverlapping ON integrations, ABAB partner chronology, session membership, durations, repeats, zero-hit-scan completeness, and the endpoint. Write exact `visits.csv` only for the exact grade; otherwise write `bounded_visits.json` with explicit assumptions and source status.
- [ ] **Step 4: Rerun `tests/test_data.py`.** Expected: PASS; local offline extraction produces validated nominal geometry and F1 schedule with distinct provenance grades. Never promote source-transcribed geometry to source-verified status.
- [ ] **Step 5: Commit.** Stage the module/contracts/tests and small normalized catalog/provenance artifacts; `git commit -m "feat: reconcile target sites and preserve schedule uncertainty"`.

## Task 3: Acquire sources with bounded streaming and expose G0

**Files:** Modify `data.py`, `budget.py`, `cli.py`; create `tests/test_acquisition.py`, `tests/test_environment.py`, tiny streaming fixtures in `tests/fixtures/`; produce `inputs/` metadata and `results/environment.json`.

**Interfaces:**

- `inspect_environment() -> dict` records hardware, RAM, disk, native/emulated architecture, Python/package/build info, threads, and power restrictions or their unavailable status.
- `acquire_sources(protocol:Protocol,catalog:Catalog,ledger:BudgetLedger) -> dict` returns immutable source records and the attained schedule/calibration grade. `stream_scan_metadata(stream:BinaryIO,expected_sha256:str,expected_bytes:int) -> dict` returns reduced unique `(source_file,NAME,SCAN,MJD)` records, small validation sample, and actual byte hash/count.
- CLI `env --out`, `acquire --config`, and `validate-data --config`; consume Task 2 catalog/schedule contracts. Acquisition I/O stays injectable for offline tests.

- [ ] **Step 1: Write failing access/integrity tests.** A synthetic 403 route is attempted at most twice and selects F1/F2; two 401s never trigger credential scraping. A stream truncated by one byte fails expected size/hash verification and cannot create a complete schedule. Assert a zero-hit target absent from candidate rows remains unverified; an injected small download-byte cap stops midstream and charges received bytes. Assert no `read()` without a bounded chunk and no full-archive materialization. Mock environment cases verify RSS cap `min(8 GiB,.25*RAM)` and required 4 GiB disk reserve.
- [ ] **Step 2: Run `tests/test_acquisition.py tests/test_environment.py` through the wrapper.** Expected: FAIL for missing bounded acquisition/preflight.
- [ ] **Step 3: Implement ordinary-access acquisition and environment commands.** Use the blueprint's pinned source versions, returned download links, Appendix C expected hashes, and exact source-status labels. Stream raw bytes once for hashing, decode CSV incrementally, and retain only unique metadata/sample unless disk permits originals. Preserve failures/status codes. A checksum proves transport integrity, not schedule completeness. Refuse oversized work before launch; stop/record on changing resource conditions.
- [ ] **Step 4: Rerun the suites and execute G0 once.** Run `env`, `acquire`, `validate-data` with `config/protocol.json`. Expected: verified metadata/catalog and exact schedule or explicit F1/F2; all attempts charged. Record source-theorem/planning-derivation identities for first attempts and dark-family noncontraction from spec §§3,6. If geometry cannot be recovered, take Task 14's analytic/data-limited exit now; do not build unused numerical machinery.
- [ ] **Step 5: Commit.** Commit code/tests and small provenance/environment summaries deliberately; `git commit -m "feat: add bounded source acquisition and feasibility gate"`.

## Task 4: Establish the scalar accepted-process oracle

**Files:** Create `src/seti_audit/model.py`, `tests/test_model.py`, `tests/test_enumeration.py`; extend `contracts.py`; add finite synthetic support in `tests/fixtures/finite_histories.json`.

**Interfaces:**

- `FirstClocks(birth_years:FloatArray,speeds:FloatArray,speed_gaps:FloatArray)` uses infinity only in memory for no attempt by horizon.
- `History(accepted_indices:IntArray,birth_years:FloatArray,speeds:FloatArray,speed_gaps:FloatArray,occupation_years:FloatArray,arrival_year:float,right_censored:bool,diagnostics:dict)` keeps accepted and suppressed events distinguishable.
- `sample_first_clocks(config:ModelConfig,geometry:Geometry,rng:Generator,conditioning:str="unconditional",horizon_years:float=100) -> FirstClocks`; support unconditional here; proposal modes arrive in Task 5. History arrays retain every site's first candidate, including suppressed candidates; accepted indices select emitters.
- `simulate_history(clocks:FirstClocks,geometry:Geometry,intersite:bool=True) -> History`; `enumerate_histories(clock_support:tuple,geometry:Geometry) -> tuple[History,...]` is an independent tiny-support oracle under `tests/`, not a second production simulator.

- [ ] **Step 1: Write failing deterministic controls.** For the two exact phantom geometries in blueprint §8.1 assert free versus accepted arrivals `2.322222...` versus `10`, and `-41.111111...` versus `+100`. Assert suppressed sources neither expand nor emit; equal-speed accepted/free earliest arrivals agree on enumerated arbitrary geometry; no clocks gives censored infinity. Assert a birth exactly at occupation is rejected, `A=0` is nonsurvival, and `A=100` is a benchmark arrival. Finite support enumerates every combination of two/three birth times and two speeds and supplies exact accepted subsets.
- [ ] **Step 2: Run `tests/test_model.py tests/test_enumeration.py` through the wrapper.** Expected: FAIL before the scalar engine.
- [ ] **Step 3: Implement hazard inversion, S1–S4 marks, and chronological propagation.** Follow blueprint §§6.1–6.3 exactly; use a stable `(birth_time,site_id)` order, permanent fronts, and no grid. Flag near ties with the specified tolerance and recompute at higher precision without moving boundaries. Ensure open-interval uniforms and stored `q` preserve `v<1`; report any rounding-safeguard count and affected mass.
- [ ] **Step 4: Rerun both suites and clock-distribution tests.** `test_piecewise_hazard_inverse` checks exact hazards on both sides of zero including `k=0`; `test_near_light_speed_support` injects endpoint-adjacent uniforms and asserts `q>0,v<1`, or a recorded precision escalation rather than a silent atom. Expected: PASS; no batch accelerator yet.
- [ ] **Step 5: Commit.** Stage model/contracts/controls; `git commit -m "feat: implement chronological accepted-birth reference"`.

## Task 5: Sample exact surviving prefixes and replay future continuations

**Files:** Modify `model.py`, `contracts.py`; create `tests/test_conditioning.py`, `tests/test_future.py`.

**Interfaces:**

- Extend `sample_first_clocks` with `conditioning="lower_cone"|"ideal_silence"`, including the hazard offset and chosen horizon.
- `sample_surviving_prefix(config:ModelConfig,geometry:Geometry,rng:Generator,max_attempts:int) -> tuple[History|None,int]`: sample only clocks through zero, reject on accepted `A<=0`, return attempts consumed and a prefix or exhaustion. `survival_constant(config:ModelConfig,geometry:Geometry) -> float` returns `C_star`.
- `FutureMarks(residual_hazards:FloatArray,speeds:FloatArray,speed_gaps:FloatArray)`; `sample_future_marks(prefix:History,config:ModelConfig,rng:Generator) -> FutureMarks`; `replay_future(prefix:History,config:ModelConfig,geometry:Geometry,marks:FutureMarks,k:float) -> History`. Draw marks once, replay all three k values from the same prefix; every primary emission/detector sees that same `k=1` history.
- `survival_diagnostic(config:ModelConfig,geometry:Geometry,rng:Generator,n_proposals:int=50000) -> tuple[int,int,float]` returns accepted/proposed counts and `C_star` for later exact intervals.

- [ ] **Step 1: Write failing conditional-distribution tests.** On Task 4 finite supports, assert every accepted survivor lies in the lower-speed cone and normalized proposal/rejection probabilities equal direct conditional probabilities. Include the pre-zero fast phantom to assert own-mark free-arrival rejection loses a valid history. For S1/S2 assert proposal rejection count is zero and `C==C_star`. Check conditional clocks invert `Lambda(l_i)+e`, not just `e`. Replay assertions: `k=0` creates no future births, a rejected pre-zero site never rebirths, `k` leaves past accepted fronts/likelihood unchanged, and `k=0,1,10` consume identical stored residual marks.
- [ ] **Step 2: Run `tests/test_conditioning.py tests/test_future.py` through the wrapper.** Expected: FAIL for missing exact proposal/replay.
- [ ] **Step 3: Implement the interfaces using blueprint §6.4.** Truncate past sampling at zero before future generation; post-zero candidates cannot affect the survival filter. Use `.1` floor for S1/S3 and `.5` for S2/S4, check attempt limits before each proposal, and charge replay evaluations. Preserve independent fixed-size diagnostics separately from survivor-stopped counts.
- [ ] **Step 4: Rerun both suites and a fixed-seed low-rate unconditional-rejection comparison.** Expected: PASS for exact enumeration; low-rate empirical discrepancies lie within predeclared diagnostic intervals. This tiny development check is not one of the 50k confirmatory diagnostics; full diagnostics wait for freeze.
- [ ] **Step 5: Commit.** `git commit -m "feat: add exact survival proposals and paired future replay"` after staging the module/contracts/tests.

## Task 6: Integrate linked survey selection and conservative weight bounds

**Files:** Create `src/seti_audit/detection.py`, `tests/test_detection.py`, `tests/test_detection_bounds.py`; extend `contracts.py`.

**Interfaces:**

- `WeightBounds(low:float,high:float)`; point weights use equal endpoints.
- `null_weight(history:History,geometry:Geometry,schedule:Schedule,emission:EmissionConfig,detector:DetectorConfig,visit_dependence:str="nominal") -> WeightBounds`.
- `source_null_weight(birth_year:float,radius_ly:float,schedule:Schedule,site_id:str,emission:EmissionConfig,detector:DetectorConfig,visit_dependence:str="nominal") -> WeightBounds` supplies the same per-source operator to Task 7 quadrature.
- `joint_activity(windows:tuple[tuple[float,float],...],on_fraction:float,corr_years:float) -> float`; `frequency_admissible(track:tuple[float,float],duration_s:float) -> bool` takes `(start_mhz,drift_hz_s)`, explicitly converting once.
- `selection_eligible(track:tuple[float,float],duration_s:float,on_hits:tuple[bool,bool],off_match:bool) -> bool` is the synthetic metadata-level selection control: frequency/drift gate, both ON hits, no OFF match. It checks declared selection logic, not raw-signal processing or empirical final calibration.

- [ ] **Step 1: Write failing known-answer tests.** One always-eligible E1/Dnom visit asserts `low==high==1-.8836`; two visits to one source with `zeta=.1` assert `w==1-.1*(2*.8836-.8836**2)`. Two separated E5 ON windows assert `G=.1*exp(-b*(d1+d2))*P11(gap)`. A two-ON hit test asserts AND bounds `.88<=p_both<=.94`, never the OR expression. Assert a masked/zero-drift/OFF-matching synthetic signal cannot pass the fixed gate, even under Duncal. Retarded-time tests place onset/end exactly on integration boundaries; partial coverage gives zero for point/full-ON scenarios but may have a Duncal upper detection bound of one.
- [ ] **Step 2: Run `tests/test_detection.py tests/test_detection_bounds.py` through the wrapper.** Expected: FAIL for missing linked weights.
- [ ] **Step 3: Implement temporal containment, exact CTMC gaps, source-level inclusion–exclusion, and source products.** Use blueprint §§5.2–5.4,6.5, including the complete fixed frequency mask. Merge overlapping required windows, retain one compatibility status, preserve conditional visit recovery assumptions, and use log products/explicit zeros. For F1 use certain/impossible/uncertain coverage, `2d` packing impossibility, unknown-gap CTMC bounds, and dependence-robust marginal unions. Shared detector settings remain shared; do not independently extremize alternating inclusion–exclusion terms.
- [ ] **Step 4: Rerun suites with finite nuisance enumeration.** `test_bounds_cover_all_schedules_and_shared_efficiencies` asserts `w_low<=w_case<=w_high` for every tiny admissible schedule, detector setting, and repeated-visit dependence case. `test_empty_sources_and_visits` asserts weight one. All probability bounds satisfy `0<=low<=high<=1`; violations fail the gate rather than being silently clipped.
- [ ] **Step 5: Commit.** `git commit -m "feat: model linked visits and bounded detector response"` after staging likelihood/contracts/tests.

## Task 7: Build the deterministic independent-site and ideal-silence controls

**Files:** Create `src/seti_audit/oracles.py`, `tests/test_oracles.py`, `tests/test_ideal_silence.py`; extend `contracts.py`.

**Interfaces:**

- `OracleResult(C:float,likelihood:WeightBounds,R0:WeightBounds,R:WeightBounds,absolute_errors:dict,joint_bounds:dict)`; all fields include explicit evidence/numerical status when not valid.
- `independent_oracle(config:ModelConfig,geometry:Geometry,schedule:Schedule,emission:EmissionConfig,detector:DetectorConfig) -> OracleResult`, consuming Task 6 `source_null_weight`.
- `ideal_silence_probability(config:ModelConfig,geometry:Geometry) -> float`; `ideal_silence_gap(geometry:Geometry,v_max:float) -> float`. Ideal histories use Task 5's `ideal_silence` clock mode and replay interface; no separate simulator.

- [ ] **Step 1: Write failing independent checks.** One-site fixed-speed ideal control asserts `p(h)=-expm1(-lambda*max(h-r*(1/v-1),0))`; no-birth atom and `mu=0` assert `C=likelihood=1,R0=R=0`. Finite-support site products equal explicit enumeration. Assert the oracle never calls a survival-proposal sampler. Ideal silence assertions: `P(S)=exp(-sum(lambda_i*max(age-r_i,0)))`, independent of speed; hard-cutoff risks vanish inside the exact gap. Compare the unconditional-clock oracle with a small independently conditioned MC control, not interacting-survivor clocks.
- [ ] **Step 2: Run `tests/test_oracles.py tests/test_ideal_silence.py` through the wrapper.** Expected: FAIL for missing exact controls.
- [ ] **Step 3: Implement one-dimensional split birth-time quadrature.** Use blueprint §6.6 speed-integrated `g(t,b)`, first-clock density and atom; split at zero, speed thresholds, emission boundaries, and relevant scan eligibility boundaries. Calculate products with log sums/`expm1`. For interval weights compute lower/upper total-null products and no-century-arrival products, then partition each corresponding bound weight into `J` and `K`; apply the spec's conservative ratios. Never assume posterior risk monotonic in detector efficiency.
- [ ] **Step 4: Rerun suites with independent numerical refinement.** Compare to tighter split integration/high precision, targeting `1e-8` absolute and `1e-6` relative above `1e-6`; assert validated main-cell error `<1e-4`. Tiny interval-nuisance enumeration must lie inside reported outer risks. Expected: PASS with recorded error evidence; an internal quadrature error estimate alone cannot pass.
- [ ] **Step 5: Commit.** `git commit -m "feat: add matched finite-site integration and silence controls"` after staging oracle/contracts/tests.

## Task 8: Independently check the finite-age theorem formulas

**Files:** Create `src/seti_audit/theorem.py`, `tests/test_theorem.py`; expose the deterministic portion of `theorem-check` in `cli.py`.

**Interfaces:**

- `finite_age_kernel(q:float,h:float,T:float,d:int) -> float`.
- `continuum_mean(h:float,alpha:float,T:float=1,d:int=3,intensity:float=1) -> float`, where `intensity=lambda*nu_d*c**d`.
- `warning_intensity(h:float,u:float,alpha:float,T:float=1,d:int=3,intensity:float=1) -> float` implements the independently repaired `L`.
- `free_joint_cdf(h:float,z:float,u:float,alpha:float) -> float` integrates `exp(-b(x))*L(x,u)/(1-exp(-b(h)))` through `zh`; tiny atomic-law adapters are private reference helpers.

- [ ] **Step 1: Write failing mathematical tests.** Assert both kernel branches agree at `q=h/T`; direct radial integral agrees relatively within `1e-9` at ordinary scale. For alpha 1 and 2 assert `b=.75*h**2+.5*h**3` and `b=h**3-.25*h**4` at `.001,.1,.5`. Verify `b'(h)=L(h,1)`, `L(h,0)=0`, joint CDF endpoints and distinction between conditioning on `H=h` and `H<=h`. An atomic speed exactly at the split must be counted once; tiny `h` must not produce cancellation zeros. Assert alpha 3 is compared to logarithmic convergence rather than a false finite-h `1e-9` limiting error.
- [ ] **Step 2: Run `tests/test_theorem.py` through the wrapper.** Expected: FAIL for missing stable formulas.
- [ ] **Step 3: Implement blueprint §§3.3,8.2 formulas.** Split quadrature, normalize tiny powers, use `log1p/expm1`, and use mpmath on the small precision-sensitive subset. Record source equations versus independent repair. Run the six alpha values and four binary64 horizons; enable `1e-12` only after high-precision convergence. Do not claim reproduction of absent source scripts.
- [ ] **Step 4: Rerun tests and the deterministic `theorem-check` mode.** Expected: PASS with source hash, exact/leading ratios, warning/derivative checks, precision, and tolerances saved under `results/theorem/`; no assertion that continuum asymptotics describe the stellar catalog.
- [ ] **Step 5: Commit.** `git commit -m "feat: verify finite-age contact and warning formulas"` after staging theorem/CLI/tests and small verification artifacts.

## Task 9: Validate accepted growth in the finite continuum shell

**Files:** Modify `theorem.py`, `cli.py`; create `tests/test_shell.py`; extend `contracts.py` with `ShellSummary`.

**Interfaces:** `sample_shell(config:dict,rng:Generator,n_histories:int,ledger:BudgetLedger) -> ShellSummary`, with config fixed to alpha 1 and `h=.02` or `.5`. `ShellSummary` records conditional trial/accepted-contact counts, free and accepted normalized warnings, censoring, b/s, and resource use; the inference/report layers calculate intervals later.

- [ ] **Step 1: Write failing shell controls.** Assert positive-truncated Poisson probabilities start at `b/expm1(b)` and follow the exact recurrence; reject `b=0`. On forced deterministic points assert the contact winner can change/be suppressed while earliest signal is unchanged. Assert an arrival beyond `T+h` is right-censored and never called the global later arrival. Finite free samples are compared to Task 8 `free_joint_cdf`, not the exact-arrival conditional CDF.
- [ ] **Step 2: Run `tests/test_shell.py` through the wrapper.** Expected: FAIL for absent shell construction.
- [ ] **Step 3: Implement only the bounded shell sampler in blueprint §8.2.** Use independent restrictions to `B_h` and its shell complement, continuous positions/times and actual chronological suppression. Recompute ambiguous truncated-CDF sums at high precision. Cap conditional histories at 10k per horizon and disallow this rejection construction at other horizons/alphas. Share the suppression semantics, without forcing continuum points through the finite-star first-clock reduction.
- [ ] **Step 4: Rerun tests and a tiny development sample.** Expected: PASS; diagnostic intervals for `(1-exp(-b))*P(accepted contact|N_B>=1)` overlap the rigorous `[b*exp(-s),1-exp(-b)]` bounds at the allocated error level. A deterministic phantom must exercise suppression even when the small random sample does not. Final reference runs are scheduled in Task 14 and together remain at most 20k histories, including these trials.
- [ ] **Step 5: Commit.** `git commit -m "feat: add bounded continuum suppression reference"` after staging the shell implementation/tests.

## Task 10: Certify compatibility, risks, and family envelopes

**Files:** Create `src/seti_audit/inference.py`, `tests/test_inference.py`, `tests/test_envelopes.py`; extend `contracts.py`.

**Interfaces:**

- `AuditCounts(histories:int,arrivals:int,nulls:int,arrival_nulls:int,sum_w:float,sum_bw:float,bound_counts:dict[str,int])`; count keys for bounded weights are `null_low,null_high,J_low,J_high,K_low,K_high`, all with denominator `histories`. Track actual attempted universes separately in batch/resource records.
- `accumulate(arrival_flags:NDArray[np.bool_],weights:FloatArray,uniforms:FloatArray) -> AuditCounts`; bounded variant `accumulate_bounds(arrival_flags,low_weights,high_weights,uniforms) -> AuditCounts` uses the same shapes/types.
- `exact_interval(successes:int,trials:int,alpha:float) -> WeightBounds`; `summarize(counts_by_cell:dict[str,AuditCounts],protocol_lock:dict) -> Summary`. `Summary` holds result rows, certified/possible model sets, `I0/Iselect/Ipost`, and claim certificates. Task 12 supplies the frozen bound registry; tests use tiny explicit registries.
- `certify_narrowing(baseline_upper:WeightBounds,post_upper:WeightBounds,has_certified_retained:bool) -> str` returns `material`, `nonmaterial`, or `inconclusive`; `summarize` handles incompatible families first. `baseline_upper` bounds the original family's maximum R0. `post_upper.low` is the maximum risk lower bound among certified-retained cells (zero if none); `post_upper.high` is the maximum risk upper bound among all possibly retained cells. These distinct sets are essential to the positive/negative rules.

- [ ] **Step 1: Write failing inference controls.** Use exact two-branch weights to assert `R0=.5,likelihood=.53,R=.5/.53` for fast/dark and `R=.03/.53` for the positive control. `test_zero_null_draws` asserts risk `[0,1]`; zero arrivals with `n>0` asserts upper bound `>0`; weighted noninteger successes must fail. `test_threshold_equality` asserts retention at `.05` and exclusion only below it. `test_interval_partition_bounds` enumerates nuisance weights and asserts every risk lies in `J-/(J-+K+)` through `J+/(J++K-)`.
- [ ] **Step 2: Run `tests/test_inference.py tests/test_envelopes.py` through the wrapper.** Expected: FAIL for missing estimates/certificates.
- [ ] **Step 3: Implement point estimates and exact Bernoulli intervals.** Use integer audit counts, the frozen Bonferroni registry, and strictly open-interval, independent-per-history uniforms paired across variants. Merge numerical error conservatively; use Task 7 quadrature errors for independent cells and fixed-diagnostic binomial intervals times `C_star` for mixed-speed C. Never assign a binomial interval to weighted sums or survivor-stopped proposal ratios. Separate lower-variance estimates from audit intervals; zero total weight gives an undefined point estimate/status and conservative risk interval, never NaN or a fabricated zero.
- [ ] **Step 4: Add and pass adversarial envelope tests.** An unresolved high-risk cell contributes `[0,1]` and blocks a false positive; an empty possible set is incompatible, never risk zero; `L0=0` blocks relative certification; failure to prove positive stays inconclusive unless the spec §3 negative inequality certifies nonmateriality. A certified retained lower post bound rules out narrowing when either maximum possible contraction is strictly below `.01` or `.25`. Invisible counterparts retain original demographic risks; threshold reuse never triples error allocation. Test open-uniform endpoints, zero total weighted denominator, and zero binomial trials explicitly. Expected: both suites PASS, including every Review Focus uncertainty case.
- [ ] **Step 5: Commit.** `git commit -m "feat: certify null compatibility and arrival envelopes"` after staging inference/contracts/tests.

## Task 11: Pass correctness, then measure batching and mechanism sensitivity

**Files:** Modify `model.py`, `cli.py`; create `src/seti_audit/experiments.py`, `tests/test_batch.py`, `tests/test_calibration.py`; extend `contracts.py` with batch representations.

**Interfaces:**

- `ClockBatch` carries Task 4 clock arrays with shape `(batch,n)`; `HistoryBatch` carries site-indexed candidate arrays, accepted masks, occupation arrays, per-history arrival/censoring arrays, and sparse diagnostics. `simulate_batch(clocks:ClockBatch,geometry:Geometry,intersite:bool=True) -> HistoryBatch`; `history_at(batch:HistoryBatch,index:int) -> History` supplies deterministic replay samples. Scalar engine remains the oracle.
- `CalibrationResult(survivor_target:int|None,logical_batch_size:int,projected_seconds:float,proposal_costs:dict[int,float],acceptance_bounds:dict[int,WeightBounds],timings:dict,rss_bytes:int,feasible:bool,evidence_ids:tuple[str,...])`; `calibrate(protocol:Protocol,catalog:Catalog,schedule:Schedule,ledger:BudgetLedger) -> CalibrationResult`. Target is `100000`, `25000`, or null when infeasible.
- `PilotResult(passed:bool,evidence_ids:tuple[str,...],controls:dict,diagnostics:dict)`; `pilot(protocol:Protocol,catalog:Catalog,schedule:Schedule,ledger:BudgetLedger) -> PilotResult` returns exact-control validation and descriptive mechanism diagnostics; never edits scientific values. Expose `calibrate --config` and `pilot --config`.

- [ ] **Step 1: Write failing batch/projection tests.** Assert pathwise equality with scalar outputs on identical clocks, including both phantoms, ties, all-surviving/all-suppressed geometries, and a partial final batch. Assert an artificially expensive full matrix selects 25k without changing models; if neither target fits at 2x cost margin, return infeasible. Memory pressure must change only physical batch size, retaining histories/precision. A noisy pilot risk must not alter `mu`, detector assumptions, sample-size policy, or thresholds.
- [ ] **Step 2: Run the new suites through the wrapper.** Expected: new behavior FAIL; previously implemented scientific controls remain passing. If an actual G1 gate fails, diagnose within the two-repair/30-minute allowance and stop comparisons if unresolved.
- [ ] **Step 3: Implement rank-wise NumPy propagation and resource projection.** Avoid `(batch,n,n)` arrays. Measure 1024/4096/feasible 16384 attempts at `mu=1,12`, S1/S3/S4 and small S4 age cases, one cold process and three warmed batches. Include imports, preparation, clocks, suppression, linked detection, quadrature, future replay, fixed 50k diagnostics, and report cost. Derive mixed-speed cost from a conservative acceptance lower bound; count every measured attempt. No accelerator unless measured necessity fits remaining repair resources.
- [ ] **Step 4: Run the full tiny-control suite as the green verification, then G2 calibration and G3 pilot.** Expected: all exact G1 invariants pass; recorded projections justify a fixed 100k/25k target or a documented early stop. Pilot two fixed development demographics (`mu=1/S1`, `mu=12/S4`) plus positive, null, sign-reversal, and bounded shell controls; empirical noisy effects are descriptive only. All pilot seeds use phase 0. Bundle CLI verification inside suites; keep total top-level development/calibration/pilot jobs within 30, including red/green tests, and leave any remaining launches for repairs.
- [ ] **Step 5: Commit.** `git commit -m "perf: validate batched histories and measured feasibility"` after staging code/tests and small G1–G3 evidence with source/config hashes.

## Task 12: Freeze the finite matrix and implement exactly resumable confirmation

**Files:** Modify `experiments.py`, `artifacts.py`, `budget.py`, `cli.py`, `contracts.py`; create `tests/test_matrix.py`, `tests/test_runner.py`, `tests/test_resume.py`, `tests/test_freeze.py`.

**Interfaces:**

- `build_matrix(protocol:Protocol,schedule:Schedule) -> tuple[dict,...]` produces unique cells with stable IDs, model kind, family membership, emission/detector/continuation IDs, and evidence grades.
- `build_bound_registry(cells:tuple[dict,...]) -> dict` enumerates unique scalar decision bounds, assigning primary or diagnostic pool and per-bound alpha. Identical shared scalars use one ID/allocation, reused at all thresholds.
- `freeze_protocol(protocol:Protocol,catalog:Catalog,schedule:Schedule,calibration:CalibrationResult,pilot:PilotResult,output_dir:Path) -> dict` writes immutable `results/protocol.lock.json`, `matrix.json`, and `bound_registry.json` with mutually validated hashes.
- `run_confirmation(protocol_lock:dict,resume:bool,ledger:BudgetLedger) -> dict`; `commit_batch(output_dir:Path,batch_id:str,payload:dict,arrays:dict) -> str`; `load_committed_batches(output_dir:Path,protocol_hash:str) -> tuple[dict,...]`.
- Expose `freeze --config`, `run --protocol`, and `run --protocol ... --resume`. Errors use exit 2 for invalid config/lock, 3 for blocking input, 4 for invalid correctness, 5 for a budget stop; reached-grade success is 0 with machine-readable limitations. Preserve partial evidence for every status.

- [ ] **Step 1: Write failing matrix and freeze tests.** Assert exactly 16 primary plus four age demographics, 16 ideal-silence ensembles, the evaluated combinations in spec §4, no E2–E5 future Cartesian expansion, and at most 2,000 unique cells. All three tau statuses share a cell. Assert pool error sums are at most `.025` each and repeated thresholds do not duplicate bound allocation. Missing G1/G2/G3 evidence, changed source hash, calibration-driven grid edits, or an unvalidated exact schedule must block freeze.
- [ ] **Step 2: Run the four suites through the wrapper.** Expected: FAIL for missing lock, matrix, and durable batching.
- [ ] **Step 3: Implement fixed IDs, seeds, and locked schedules.** Primary model IDs `0..15` iterate mu then S1–S4; diagnostic IDs `16..19` iterate ages then S1/S4. Use `Generator(PCG64(SeedSequence([20261101,phase,stage_id,model_id,purpose_id,batch_id])))`; phase 0/1 separates development/confirmation. Freeze purpose IDs for clocks, marks, future hazards, audit uniforms, C diagnostics, ideal histories, and shell histories, and freeze logical batch boundaries. Physical microbatching may change only with pathwise equality and unchanged logical draws. Shared-history variants reuse the same uniform; independent histories do not.
- [ ] **Step 4: Implement capped confirmation and durable resume.** Run mixed settings round-robin with separate fixed 50k C diagnostics and independent survivor draws. End each cell at its predetermined target or proposal cap, independent of null/arrival outcomes. Reserve cost before work, stage payload plus hashes, atomically publish it, and append one commit record per stable batch ID. Recover valid orphan batches by hash/identity without choosing outcomes; reconcile pending cost even when no batch can be recovered. Reject changed lock/dependency identity, duplicate IDs, corrupted counts, or conflicting artifacts. Save completion eligibility, failures, partial counts, and repair/deviation records. A completed predeclared attempt-cap design may use its valid intervals without pretending to reach the survivor target. An arbitrary wall-time truncation remains unresolved unless a separately valid predetermined design completed; summarize all unexecuted cells conservatively.
- [ ] **Step 5: Pass fault-injection and green suites.** Crash before write, after publication, before manifest append, and after commit: resumed integer counts/RNG identities equal an uninterrupted tiny run, committed batches count once, and spent budget never decreases. Test cap exhaustion, interrupted C diagnostics, simultaneous-writer rejection, corrupted checkpoint, changed NumPy/requirements lock, and report-reserve enforcement. Expected: all four suites PASS; this is a tiny synthetic design, not confirmation.
- [ ] **Step 6: Commit.** `git commit -m "feat: freeze scientific protocol and resume evidence safely"` after staging runner/storage/CLI/contracts/tests.

## Task 13: Produce evidence-only reports and a complete offline smoke path

**Files:** Create `src/seti_audit/reporting.py`, `tests/test_reporting.py`, `tests/test_cli.py`; modify `cli.py`, `README.md`, `.gitignore`; add tiny complete/blocked/invalid result fixtures under `tests/fixtures/`.

**Interfaces:**

- `render_report(results_dir:Path,output_dir:Path) -> dict` validates and reads saved protocol, results, provenance, numerical evidence, and failures; returns paths/hashes for tables, figures, report, and conclusions. No RNG or network access.
- `run_smoke(protocol:Protocol,output_dir:Path,ledger:BudgetLedger) -> dict` uses one explicitly synthetic history, linked weight, Bernoulli interval, and report row. Expose `smoke --config` and `report --protocol [--from-results]`; both report forms only consume saved evidence.
- Row schema: `cell_id,family_ids,model_kind,model_id,k,emission_id,detector_id,schedule_grade,detector_grade,C,likelihood,R0,R,intervals,numerical_errors,compatibility,attempted,surviving,nulls,arrivals,completion_status,failure_ids,evidence_ids,protocol_hash`. `conclusions.json` contains `claim_id,claim,outcome_category,scope,evidence_ids,unresolved_dependencies` for each claim.

- [ ] **Step 1: Write failing report/CLI tests.** Patch acquisition and RNG entry points to raise during regeneration; a valid report still succeeds. Assert a missing mandatory result remains an unresolved row and outer-envelope contributor; a blocked calibration remains F2; a fully excluded family has null risk/status rather than zero. Assert all five outcome categories are representable per claim, each conclusion's evidence IDs resolve, and synthetic fixture rows are visibly synthetic. A theorem failure can coexist with independently validated finite-site claims.
- [ ] **Step 2: Run `tests/test_reporting.py tests/test_cli.py` through the wrapper.** Expected: FAIL for absent report/smoke behavior.
- [ ] **Step 3: Implement reports and reproduction instructions.** Render the spec §10 report contents and four required static figure families, or justified table substitutes; label model families, uncertainty, data grade, and source/configuration IDs. Preserve signed risk increases and distinguish weighted estimates from certified intervals. Emit explicit null/status for undefined values and list every unperformed validation. Document setup, every supported CLI command, data limits, exact source hashes, ledger/resume behavior, and `report --from-results`. A partial/analytic stop still gets an evidence report without pretending to have numerical outputs.
- [ ] **Step 4: Pass green end-to-end suites.** In an isolated temp project, verify installed package dispatch, all required subcommand parsers, smoke under 60 seconds after setup, deterministic pause/resume, and two evidence-only report regenerations with identical table/conclusion contents. Check finite JSON, CSV schema, artifact links/hashes, missing-file error classification, memory/disk reserve preflight, and the attained-grade README. Expected: both suites PASS; include setup/import/report costs once in the ledger.
- [ ] **Step 5: Commit.** `git commit -m "feat: report scoped research evidence and reproduction paths"` after staging reporting/CLI/docs/tests.

## Task 14: Execute only the frozen work that the gates permit

**Files/artifacts:** Produce `results/protocol.lock.json`, `matrix.json`, `bound_registry.json`, manifests/checkpoints/aggregate results, failures/deviations, `tables/`, `conclusions.json`, `report/REPORT.md`, `report/figures/`; update `README.md`. Input and normalized-data paths remain as defined in Tasks 2–3. Retain at most 1 GiB generated artifacts; no complete trajectory dump.

**Interfaces:** Consume Task 12 frozen runner and Task 13 report renderer. This is execution of the research, not another software feature; reuse the validated tests instead of writing implementation-mirroring tests.

- [ ] **Step 1: Confirm the attained G0–G3 evidence and remaining ledger.** Reuse already completed source acquisition, correctness, calibration, and pilot artifacts; do not reset their cost or rerun to seek favorable outcomes. If G0 geometry, G1 correctness, or G2 cost stopped the audit, jump to Step 4 with that precise reason and analytic evidence. F1/F2 alone do not stop unaffected math/computation. Record any post-freeze scientific change as a dated deviation requiring independent fresh evidence within the original budget, otherwise exploratory.
- [ ] **Step 2: Freeze once and run G4.** `python -m seti_audit freeze --config config/protocol.json`, then `python -m seti_audit run --protocol results/protocol.lock.json`. Expected: immutable source/schedule grades, target size, caps, complete matrix and alpha registry, separate mixed-speed fixed diagnostics, and fresh phase-1 evidence for all 16 primary demographics. Use the original lock with `--resume` after interruption. No inference outcome controls runtime or model inclusion.
- [ ] **Step 3: Complete G5 only within its remaining allowance.** The runner reuses prefixes for E1/E0 `k=0,10`, runs the four age diagnostics, direct ideal-silence samples and futures, detector/emission variants, dependence bounds, continuous Dpositive/F1 weights, and the remaining bounded continuum references. G4/G5 nominal allowances are 190/45 minutes; protect G6's 35 minutes and remaining global caps. Preserve incomplete mandatory rows and scope-qualified conclusions. E0/Duncal obstruction is analytical, never a large extra simulation.
- [ ] **Step 4: Regenerate and review attained evidence in G6.** Run `python -m seti_audit report --protocol results/protocol.lock.json --from-results`; on a pre-freeze early stop use the reporting module's partial-results path with the saved configuration/provenance and no invented lock. Repeat the blueprint §13 mathematics, experimental, and execution passes; record only material findings/dispositions. Verify positive and negative certificates against saved intervals, the inclusion of every unresolved cell, exact-versus-F1 wording, F2 assumptions, full-dark obstruction, report/table agreement, all costs including failures, and clean-install/smoke evidence already obtained.
- [ ] **Step 5: Commit the reached result.** Stage small configs, hashes, aggregates, failures, evidence tables/conclusions/report/figures and final usage; verify the staged diff contains no bulk archive or secrets. `git commit -m "research: record scoped SETI null audit and evidence limits"`. State the attained claim categories, actual verified commands, unfinished work, costs, and the smallest missing input. A justified early stop completes this task without manufacturing later results.

## Coverage and plan review

| Specification requirement | Owning tasks / decisive evidence |
|---|---|
| §1 source authority and source/derivation distinction | 1–3, 8, 13–14: unchanged hashes and evidence labels |
| §2 scope, exclusions, staged approach | 3, 11–14: explicit grades/gates; no smaller scientific grid |
| §3 quantities, compatibility, material/negative/invisible rules | 10: exact updating controls, empty/unresolved sets, conservative certificates |
| §4 complete finite matrix and continuations | 1, 5, 12: config/matrix counts, shared prefixes, no accidental Cartesian claims |
| §5 catalog, schedule, acquisition and fallback | 2–3: identity, signed coordinates, completeness, streamed hash, F1/F2 |
| §6 scalar semantics and exact survival | 4–5: phantoms, finite enumeration, lower-cone sampling, future invariance |
| §6 linked selection and bounded response | 6: shared status, CTMC, temporal/frequency gates, enumerated nuisance coverage |
| §6 matched independent/ideal controls | 7: unconditional-clock quadrature, own survival, atom, exact silence gap |
| §6 continuum reference and source repair | 8–9: radial/closed-form/high-precision checks, atomic endpoints, shell censoring |
| §7 numerical/statistical assurance | 7–10, 12: refinements, integer intervals, fixed bound registry and diagnostics |
| §8 budgets, seeds, freeze, failures/resume | 1, 3, 11–12, 14: durable accounting, measured projections, interruption tests |
| §9 package/artifact/CLI contracts | 1–13: typed interfaces, parser/smoke tests, complete safe artifacts |
| §10 acceptance/report/early stop | 3, 11, 13–14: validated gates, evidence-only regeneration, per-claim categories |
| §11 design review | Recorded in approved spec; this plan receives the author's coverage/interface review |

Author self-review checked coverage against the approved spec, consistent names/types across interfaces, concrete task verification, the five Review Focus cases, and proportion. It clarified completed attempt-cap versus arbitrary-timeout behavior, distinct model sets for positive/negative certification, the metadata-only OFF-direction control, active budget enforcement, and open-uniform/zero-weight boundaries. No specification requirement was left without an owning task. This plan defines decisions and test assertions rather than full implementation bodies. Mark implementation checkboxes only as their work actually completes; none are completed by writing this plan.

Implementation handoff requires a separate user instruction. Both Superpowers execution methods remain available; keep the approved current-branch constraint. Native execution avoids repeated context handoffs across these tightly shared scientific interfaces; subagent-driven execution adds an independent review per task at greater context cost. Neither implementation nor research execution is authorized merely by approval to write this plan.
