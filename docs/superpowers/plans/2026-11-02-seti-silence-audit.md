# SETI Silence Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a reproducible, uncertainty-qualified finite-target audit of how the UCLA radio null changes century-arrival probability envelopes, including the required conditional, robustness, and validation results.

**Architecture:** One Python package shares demographic histories across emission/detector variants. A scalar suppression engine, exact conditional sampler, linked likelihood, deterministic independent oracle, and separate continuum reference feed a frozen experiment matrix and aggregate-only reporting. Build and validate the mathematical controls before the full runner; acquisition/calibration failures select the declared evidence grade rather than fabricated inputs.

**Tech Stack:** Python 3.12 or newer; NumPy, SciPy, Matplotlib, pytest, mpmath; standard-library argparse, dataclasses, CSV/JSON, urllib, hashlib, pathlib, datetime, and atomic filesystem writes. Verify and lock successful versions on the actual machine.

**Spec:** [Approved research and software specification](../specs/2026-11-02-seti-silence-audit-design.md). Read it alongside [the normative blueprint](../../blueprint.md) and [the mathematical reference](../../silence_contact_theorem.pdf). No package, tests, or CLI exists yet; commands below are implementation targets.

## Global Constraints

- Primary goal: complete the required research, robustness comparisons, and validation; no artificial elapsed-time, acquisition, workload, launch, repair, or reporting-cell caps.
- Use CPU binary64; no MPS/float32 substitution, cloud compute, CUDA, or paid services.
- Record elapsed time, RSS, disk use, downloads, evaluated histories, failures, repairs, and replays for reproducibility and optimization; resource accounting does not impose a stop quota.
- Adapt batching, streaming, compression, and checkpointing to actual available memory and storage; a demonstrated physical resource obstacle requires measured requirements, attempted remedies, and continued unaffected work.
- The scientific matrix has 20 interacting demographic settings and 16 ideal-silence reference settings; precision extensions and reruns for repairs do not change the declared scientific family.
- Initial precision checkpoints: 100,000 primary survivors; 25,000 per age/ideal-silence setting; 50,000 proposals per mixed-speed diagnostic; 10,000 shell histories per reference horizon. These are starting plans, not sample ceilings or grounds for a cost-only precision downgrade.
- Predeclare cumulative sample checkpoints `n_j=n_1*2**(j-1)` and interval error `alpha=A/(M*j*(j+1))` for registry item/checkpoint pairs; continue validated precision work when the claim remains computationally unresolved.
- Development seeds: `SeedSequence([20261101,0,...])`; confirmation seeds: `SeedSequence([20261101,1,...])`; stable integer IDs, recorded generator and NumPy version.
- Freeze scientific families, effect thresholds, source/data grades and hashes, initial checkpoint sizes, extension sequence, interval registry/error allocation, seeds, and numerical tolerances before confirmation; ordinary precision extensions preserve the lock, while scientific changes need a dated deviation and fresh independent evidence.
- A checkpoint/resume interruption leaves work pending; it never establishes completion, incompatibility, a negative result, or infeasibility. An analytic proof resolves only the claims it actually proves.

Continue on the user's current branch, `main`; do not create a worktree or switch branches. Preserve the theorem PDF hash and verify the revised blueprint hash in the specification; the original inputs remain in git history. Use the matrix, grades, inequalities, and numerical tolerances in spec §§3–8 exactly. Dnom/Dweak/Dhigh are assumptions, not calibrated confidence limits. Keep fully invisible counterparts analytic. This documentation delivery does not implement or run the research.

## Review Focus

1. **A crash between job logging, batch write, and checkpoint:** resumed work must not duplicate evidence or lose resource-use records; Task 12 fault injection.
2. **A source absent from candidate rows or a truncated final CSV:** plausible timestamps must not certify a complete schedule; Tasks 2–3 completeness and interrupted-stream tests.
3. **Boundary ties, negative-zero coordinates, and endpoint uniforms:** preserve exact event inequalities, geometry signs, and subluminal support; Tasks 2, 4, and 8 deterministic controls.
4. **No null draws, an empty retained family, or a pending high-risk cell:** retain uncertainty, continue required precision work, and distinguish incompatibility from zero risk; Task 10 decision tests.
5. **Repeated observations with a shared source status and partially illuminated scans:** never redraw compatibility, infer independent visits, or apply full-ON calibration to a partial signal; Task 6 linked and bounded tests.

---

## File structure and execution conventions

| Planned file(s) | Responsibility / owning task |
|---|---|
| `pyproject.toml`, `README.md`, `requirements.lock.txt`, `.gitignore` | Package/setup; Task 1, completed in Task 13 |
| `config/protocol.json` | Scientific defaults, precision checkpoints, and uncertainty allocation; Task 1 |
| `src/seti_audit/contracts.py` | Shared dataclasses and validated schemas, extended by the task introducing each type |
| `src/seti_audit/resources.py`, `artifacts.py` | Resource accounting and atomic artifacts; Task 1, checkpoint behavior Task 12 |
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

Tests use tiny offline fixtures, not archive downloads or full confirmation. Run a red test before implementing each behavior and the named suite afterward. After Task 1, record computational checks as `python -m seti_audit run-logged --stage G1 -- python -m pytest <paths> -q`; this wrapper records resource usage without any time/work quota. Until it exists, preserve bootstrap timings in `results/bootstrap-usage.jsonl` and import them once. Logging must not become an obstacle to useful work. Use isolated test artifacts and commit each meaningful checkpoint on `main`.

## Task 1: Create a package with resource logging and artifact integrity

**Files:** Create `pyproject.toml`, `config/protocol.json`, `src/seti_audit/{__init__,__main__,cli,contracts,resources,artifacts}.py`, `tests/conftest.py`, `tests/test_resources.py`, `tests/test_artifacts.py`, `tests/test_protocol.py`, initial `README.md`; modify `.gitignore`; generate `requirements.lock.txt` only after successful imports.

**Interfaces:**

- `load_protocol(path: Path) -> Protocol`; typed `Protocol` owns model/emission/detector lists, thresholds, seed roots, initial sample checkpoints, extension/error-allocation policy, and numerical tolerances from spec §§3–8. Shared contracts: `ModelConfig(model_id:int,mu:float,age_years:float,speed_id:str,future_multiplier:float)`, `EmissionConfig(emission_id:str,zeta:float,delay_years:float,lifetime_years:float|None,activity:str)`, `DetectorConfig(detector_id:str,pair_low:float,pair_high:float,allow_partial:bool)`. E5 constants live in emission configuration.
- `ResourceLedger(path: Path)`: `start(stage:str,ensemble_id:int|None=None) -> str`; `finish(job_id:str,elapsed_seconds:float,history_evaluations:int,download_bytes:int=0) -> None`. Persist job identity before launch and reconcile interrupted records; measure resource use without refusing work because of elapsed time or workload counts.
- `canonical_hash(value: object) -> str`, `write_json_atomic(path: Path,value: object) -> str`, `read_json_checked(path: Path,expected_hash:str|None=None) -> dict`. Canonical JSON uses sorted keys, UTF-8, finite values, and a recorded schema version.
- `main(argv: list[str]|None=None) -> int`; provide `run-logged --stage <gate> -- <command>` and package dispatch now. Add scientific subcommands in their owning tasks.

- [x] **Step 1: Write failing contract tests.** `test_usage_does_not_terminate_work` asserts large recorded duration/evaluation counts never reject a new job; `test_job_record_survives_crash` asserts pending jobs preserve identity and usage. Canonical hashes survive key order changes and nonfinite JSON fails. Assert the exact scientific grid, thresholds `[.01,.05,.10]`, checkpoint/error policy, revised blueprint hash, unchanged PDF hash, and exactly-once bootstrap record import.
- [x] **Step 2: Run `python -m pytest tests/test_resources.py tests/test_artifacts.py tests/test_protocol.py -q`.** Expect missing package/contracts first; after package discovery exists, confirm assertions fail for the intended behavior. Record bootstrap duration.
- [x] **Step 3: Implement the contracts, resource records, atomic JSON, and minimal CLI.** Use an installable `src` package, Python `>=3.12`, and the five required dependencies. Serialize append-only job records, lock writers, and reject concurrent mutation. Monitor actual RAM/disk to adapt batching and checkpoint around physical obstacles. Do not implement execution quotas, reporting reserves, or repair limits. Ignore caches, local environments, and bulk downloads without hiding deliberately retained evidence.
- [x] **Step 4: Install locally and run the three suites through `run-logged`.** Expected: PASS, ledger reflects bootstrap plus verification once; `python -m seti_audit --help` exits 0. Verify imports, installed SciPy exact-binomial API, and `python -m pip freeze > requirements.lock.txt`; do not claim a supported environment if installation/import fails.
- [x] **Step 5: Commit.** `git add pyproject.toml config src tests README.md requirements.lock.txt .gitignore`; `git commit -m "feat: add reproducible audit package and resource logging"`.

## Task 2: Normalize the physical catalog and graded schedules

**Files:** Create `src/seti_audit/data.py`, `tests/test_data.py`, `tests/fixtures/schedule_cases.json`; extend `contracts.py`; produce `data/source_rows.csv`, `data/targets.csv`, `data/provenance.json` from local sources when validated.

**Interfaces:**

- `Geometry(site_ids:tuple[str,...],xyz_ly:FloatArray,radii_ly:FloatArray,distances_ly:FloatArray)`; `Catalog(source_rows:tuple[dict,...],geometry:Geometry,provenance:dict)`.
- `Scan(visit_id:str,site_id:str,scan_index:int,start_year:float,duration_year:float,paired_visit_id:str)`; `BoundedVisit(visit_id:str,site_id:str,allowed_intervals:tuple[tuple[float,float],...],duration_year:float)`; `Schedule(exact_scans:tuple[Scan,...],bounded_visits:tuple[BoundedVisit,...],schedule_grade:str,detector_grade:str,endpoint:dict,provenance:dict)`. Validate one representation per schedule. Interval windows and durations use observer time relative to zero.
- `load_catalog(blueprint_path:Path,output_dir:Path) -> Catalog`; `load_schedule(catalog:Catalog,input_dir:Path,output_dir:Path) -> Schedule`; `validate_schedule(schedule:Schedule,catalog:Catalog,completeness:dict) -> dict`. Exact grade requires a source-backed completeness record, never a self-asserted flag.

- [x] **Step 1: Write failing geometry/grade tests.** Assert 62 rows become 61 sites; TOI 1730.01 has two linked visit rows; signed `-00:40:22.03` gives negative z; nearest radius is approximately `30.7891621` ly; precisely six unique sites have `r<100`. Assert contradictory duplicate geometry is rejected, all distance diagonals equal zero, and the matrix is symmetric. For two exact scans without completeness evidence, assert grade is not `exact`. F1 assertions: two allowed date components for each group, endpoint May 13–15 2023 UTC, 150-second durations, and no fabricated exact timestamps.
- [x] **Step 2: Run `tests/test_data.py` through the logging wrapper.** Expected: FAIL for absent catalog/schedule behavior.
- [x] **Step 3: Implement parsing and schedule validation.** Retain string identifiers and all original row provenance; use the spec's exact parsec conversion and 3D formula. Implement interval subtraction/union with no arbitrary date imputation. Exact schedule validation checks two nonoverlapping ON integrations, ABAB partner chronology, session membership, durations, repeats, zero-hit-scan completeness, and the endpoint. Write exact `visits.csv` only for the exact grade; otherwise write `bounded_visits.json` with explicit assumptions and source status.
- [x] **Step 4: Rerun `tests/test_data.py`.** Expected: PASS; local offline extraction produces validated nominal geometry and F1 schedule with distinct provenance grades. Never promote source-transcribed geometry to source-verified status.
- [x] **Step 5: Commit.** Stage the module/contracts/tests and small normalized catalog/provenance artifacts; `git commit -m "feat: reconcile target sites and preserve schedule uncertainty"`.

## Task 3: Acquire sources with streaming and expose G0

**Files:** Create `src/seti_audit/acquisition.py`; modify `data.py`, `resources.py`, `cli.py`; create `tests/test_acquisition.py`, `tests/test_environment.py`, tiny streaming fixtures in `tests/fixtures/`; produce `inputs/` metadata and `results/environment.json`.

**Interfaces:**

- `inspect_environment() -> dict` records hardware, RAM, disk, native/emulated architecture, Python/package/build info, threads, and power restrictions or their unavailable status.
- `acquire_sources(protocol:Protocol,catalog:Catalog,ledger:ResourceLedger) -> dict` returns immutable source records and the attained schedule/calibration grade. `stream_scan_metadata(stream:BinaryIO,expected_sha256:str,expected_bytes:int) -> dict` returns reduced unique `(source_file,NAME,SCAN,MJD)` records, small validation sample, and actual byte hash/count.
- CLI `env --out`, `acquire --config`, and `validate-data --config`; consume Task 2 catalog/schedule contracts. Acquisition I/O stays injectable for offline tests.

- [x] **Step 1: Write failing access/integrity tests.** Transient failures back off and resume; persistent 403/401 responses preserve the actual access obstacle and never trigger credential scraping. An arbitrary retry count or elapsed duration cannot select F1/F2. A truncated stream fails size/hash checks and cannot certify schedule completeness; a zero-hit source absent from candidate rows remains unverified. Assert incremental bounded-chunk reads and no full-archive materialization. Mock physical memory/storage changes to verify adaptive batching or a resumable interruption, not a fabricated fixed byte quota.
- [x] **Step 2: Run `tests/test_acquisition.py tests/test_environment.py` through the logging wrapper.** Expected: FAIL for missing bounded acquisition/preflight.
- [x] **Step 3: Implement ordinary-access acquisition and environment commands.** Use pinned source versions, returned public/authorized links, expected hashes, and exact evidence labels. Stream and hash raw bytes, decode CSV incrementally, and retain reduced metadata/samples. Preserve failures, backoff/recovery details, and actual bytes. A checksum proves transport integrity, not schedule completeness. Respond to actual physical constraints without imposing a time/download quota; pursue ordinary recovery paths and establish the specific access/completeness obstacle before selecting F1/F2.
- [x] **Step 4: Rerun suites and execute G0.** Run `env`, `acquire`, and `validate-data` with `config/protocol.json`. Expected: verified sources/catalog and an exact schedule or explicit F1/F2 supported by the actual missing evidence. Record first-attempt and dark-family derivations. If geometry remains unavailable after ordinary recovery, document that empirical blocker and continue independent theorem, selection, and analytic work; do not mark the whole research complete.
- [x] **Step 5: Commit.** Commit code/tests and small provenance/environment summaries deliberately; `git commit -m "feat: add streaming acquisition and evidence grading"`.

## Task 4: Establish the scalar accepted-process oracle

**Files:** Create `src/seti_audit/model.py`, `tests/test_model.py`, `tests/test_enumeration.py`; extend `contracts.py`; add finite synthetic support in `tests/fixtures/finite_histories.json`.

**Interfaces:**

- `FirstClocks(birth_years:FloatArray,speeds:FloatArray,speed_gaps:FloatArray)` uses infinity only in memory for no attempt by horizon; an optional diagnostics field records uniform/rounding safeguards.
- `History(accepted_indices:IntArray,birth_years:FloatArray,speeds:FloatArray,speed_gaps:FloatArray,occupation_years:FloatArray,arrival_year:float,right_censored:bool,diagnostics:dict)` keeps accepted and suppressed events distinguishable; `survives` and `arrives_within_horizon` preserve high-precision boundary classifications.
- `sample_first_clocks(config:ModelConfig,geometry:Geometry,rng:Generator,conditioning:str="unconditional",horizon_years:float=100) -> FirstClocks`; support unconditional here; proposal modes arrive in Task 5. History arrays retain every site's first candidate, including suppressed candidates; accepted indices select emitters.
- `simulate_history(clocks:FirstClocks,geometry:Geometry,intersite:bool=True) -> History`; `enumerate_histories(clock_support:tuple,geometry:Geometry) -> tuple[History,...]` is an independent tiny-support oracle under `tests/`, not a second production simulator.

- [x] **Step 1: Write failing deterministic controls.** For the two exact phantom geometries in blueprint §8.1 assert free versus accepted arrivals `2.322222...` versus `10`, and `-41.111111...` versus `+100`. Assert suppressed sources neither expand nor emit; equal-speed accepted/free earliest arrivals agree on enumerated arbitrary geometry; no clocks gives censored infinity. Assert a birth exactly at occupation is rejected, `A=0` is nonsurvival, and `A=100` is a benchmark arrival. Finite support enumerates every combination of two/three birth times and two speeds and supplies exact accepted subsets.
- [x] **Step 2: Run `tests/test_model.py tests/test_enumeration.py` through the logging wrapper.** Expected: FAIL before the scalar engine.
- [x] **Step 3: Implement hazard inversion, S1–S4 marks, and chronological propagation.** Follow blueprint §§6.1–6.3 exactly; use a stable `(birth_time,site_id)` order, permanent fronts, and no grid. Flag near ties with the specified tolerance and recompute at higher precision without moving boundaries. Ensure open-interval uniforms and stored `q` preserve `v<1`; report any rounding-safeguard count and affected mass.
- [x] **Step 4: Rerun both suites and clock-distribution tests.** `test_piecewise_hazard_inverse` checks exact hazards on both sides of zero including `k=0`; `test_near_light_speed_support` injects endpoint-adjacent uniforms and asserts `q>0,v<1`, or a recorded precision escalation rather than a silent atom. Expected: PASS; no batch accelerator yet.
- [x] **Step 5: Commit.** Stage model/contracts/controls; `git commit -m "feat: implement chronological accepted-birth reference"`.

## Task 5: Sample exact surviving prefixes and replay future continuations

**Files:** Modify `model.py`, `contracts.py`; create `tests/test_conditioning.py`, `tests/test_future.py`.

**Interfaces:**

- Extend `sample_first_clocks` with `conditioning="lower_cone"|"ideal_silence"`, including the hazard offset and chosen horizon.
- `sample_surviving_prefix(config:ModelConfig,geometry:Geometry,rng:Generator) -> tuple[History,int]`: sample clocks through zero, reject on accepted `A<=0`, and return a surviving prefix with its proposal count. The batch owner records returned counts and checkpoints interruptions; there is no attempt quota. `survival_constant(config:ModelConfig,geometry:Geometry) -> float` returns `C_star`.
- `FutureMarks(residual_hazards:FloatArray,speeds:FloatArray,speed_gaps:FloatArray)`; `sample_future_marks(prefix:History,config:ModelConfig,rng:Generator) -> FutureMarks`; `replay_future(prefix:History,config:ModelConfig,geometry:Geometry,marks:FutureMarks,k:float) -> History`. Draw marks once, replay all three k values from the same prefix; every primary emission/detector sees that same `k=1` history.
- `survival_diagnostic(config:ModelConfig,geometry:Geometry,rng:Generator,n_proposals:int=50000) -> tuple[int,int,float]` returns accepted/proposed counts and `C_star` for checkpoint-adjusted intervals. The default is an initial precision plan; the runner accumulates further predetermined proposal checkpoints as needed.

- [x] **Step 1: Write failing conditional-distribution tests.** On Task 4 finite supports, assert every accepted survivor lies in the lower-speed cone and normalized proposal/rejection probabilities equal direct conditional probabilities. Include the pre-zero fast phantom to assert own-mark free-arrival rejection loses a valid history. For S1/S2 assert proposal rejection count is zero and `C==C_star`. Check conditional clocks invert `Lambda(l_i)+e`, not just `e`. Replay assertions: `k=0` creates no future births, a rejected pre-zero site never rebirths, `k` leaves past accepted fronts/likelihood unchanged, and `k=0,1,10` consume identical stored residual marks.
- [x] **Step 2: Run `tests/test_conditioning.py tests/test_future.py` through the logging wrapper.** Expected: FAIL for missing exact proposal/replay.
- [x] **Step 3: Implement blueprint §6.4 interfaces.** Truncate past sampling at zero before future generation. Use `.1` floor for S1/S3 and `.5` for S2/S4, record all proposals/replays, and checkpoint operational interruptions. Keep proposal-count diagnostics independent of survivor-stopped counts and extend both under the frozen checkpoint scheme.
- [x] **Step 4: Rerun both suites and a fixed-seed low-rate unconditional-rejection comparison.** Expected: PASS for exact enumeration; low-rate empirical discrepancies lie within predeclared diagnostic intervals. This tiny development check is not one of the 50k confirmatory diagnostics; full diagnostics wait for freeze.
- [x] **Step 5: Commit.** `git commit -m "feat: add exact survival proposals and paired future replay"` after staging the module/contracts/tests.

## Task 6: Integrate linked survey selection and conservative weight bounds

**Files:** Create `src/seti_audit/detection.py`, `tests/test_detection.py`, `tests/test_detection_bounds.py`; extend `contracts.py`.

**Interfaces:**

- `WeightBounds(low:float,high:float)`; point weights use equal endpoints and an optional `rechecks` field preserves temporal boundary audits.
- `null_weight(history:History,geometry:Geometry,schedule:Schedule,emission:EmissionConfig,detector:DetectorConfig,visit_dependence:str="nominal") -> WeightBounds`.
- `source_null_weight(birth_year:float,radius_ly:float,schedule:Schedule,site_id:str,emission:EmissionConfig,detector:DetectorConfig,visit_dependence:str="nominal") -> WeightBounds` supplies the same per-source operator to Task 7 quadrature.
- `joint_activity(windows:tuple[tuple[float,float],...],on_fraction:float,corr_years:float) -> float`; `frequency_admissible(track:tuple[float,float],duration_s:float) -> bool` takes `(start_mhz,drift_hz_s)`, explicitly converting once.
- `selection_eligible(track:tuple[float,float],duration_s:float,on_hits:tuple[bool,bool],off_match:bool) -> bool` is the synthetic metadata-level selection control: frequency/drift gate, both ON hits, no OFF match. It checks declared selection logic, not raw-signal processing or empirical final calibration.

- [x] **Step 1: Write failing known-answer tests.** One always-eligible E1/Dnom visit asserts `low==high==1-.8836`; two visits to one source with `zeta=.1` assert `w==1-.1*(2*.8836-.8836**2)`. Two separated E5 ON windows assert `G=.1*exp(-b*(d1+d2))*P11(gap)`. A two-ON hit test asserts AND bounds `.88<=p_both<=.94`, never the OR expression. Assert a masked/zero-drift/OFF-matching synthetic signal cannot pass the fixed gate, even under Duncal. Retarded-time tests place onset/end exactly on integration boundaries; partial coverage gives zero for point/full-ON scenarios but may have a Duncal upper detection bound of one.
- [x] **Step 2: Run `tests/test_detection.py tests/test_detection_bounds.py` through the logging wrapper.** Expected: FAIL for missing linked weights.
- [x] **Step 3: Implement temporal containment, exact CTMC gaps, source-level inclusion–exclusion, and source products.** Use blueprint §§5.2–5.4,6.5, including the complete fixed frequency mask. Merge overlapping required windows, retain one compatibility status, preserve conditional visit recovery assumptions, and use log products/explicit zeros. For F1 use certain/impossible/uncertain coverage, `2d` packing impossibility, unknown-gap CTMC bounds, and dependence-robust marginal unions. Shared detector settings remain shared; do not independently extremize alternating inclusion–exclusion terms.
- [x] **Step 4: Rerun suites with finite nuisance enumeration.** `test_bounds_cover_all_schedules_and_shared_efficiencies` asserts `w_low<=w_case<=w_high` for every tiny admissible schedule, detector setting, and repeated-visit dependence case. `test_empty_sources_and_visits` asserts weight one. All probability bounds satisfy `0<=low<=high<=1`; violations fail the gate rather than being silently clipped.
- [x] **Step 5: Commit.** `git commit -m "feat: model linked visits and bounded detector response"` after staging likelihood/contracts/tests.

## Task 7: Build the deterministic independent-site and ideal-silence controls

**Files:** Create `src/seti_audit/oracles.py`, `tests/test_oracles.py`, `tests/test_ideal_silence.py`; extend `contracts.py`.

**Interfaces:**

- `OracleResult(C:float,likelihood:WeightBounds,R0:WeightBounds,R:WeightBounds,absolute_errors:dict,joint_bounds:dict)`; all fields include explicit evidence/numerical status when not valid.
- `independent_oracle(config:ModelConfig,geometry:Geometry,schedule:Schedule,emission:EmissionConfig,detector:DetectorConfig) -> OracleResult`, consuming Task 6 `source_null_weight`.
- `ideal_silence_probability(config:ModelConfig,geometry:Geometry) -> float`; `ideal_silence_gap(geometry:Geometry,v_max:float) -> float`. Ideal histories use Task 5's `ideal_silence` clock mode and replay interface; no separate simulator.

- [x] **Step 1: Write failing independent checks.** One-site fixed-speed ideal control asserts `p(h)=-expm1(-lambda*max(h-r*(1/v-1),0))`; no-birth atom and `mu=0` assert `C=likelihood=1,R0=R=0`. Finite-support site products equal explicit enumeration. Assert the oracle never calls a survival-proposal sampler. Ideal silence assertions: `P(S)=exp(-sum(lambda_i*max(age-r_i,0)))`, independent of speed; hard-cutoff risks vanish inside the exact gap. Compare the unconditional-clock oracle with a small independently conditioned MC control, not interacting-survivor clocks.
- [x] **Step 2: Run `tests/test_oracles.py tests/test_ideal_silence.py` through the logging wrapper.** Expected: FAIL for missing exact controls.
- [x] **Step 3: Implement one-dimensional split birth-time quadrature.** Use blueprint §6.6 speed-integrated `g(t,b)`, first-clock density and atom; split at zero, speed thresholds, emission boundaries, and relevant scan eligibility boundaries. Calculate products with log sums/`expm1`. For interval weights compute lower/upper total-null products and no-century-arrival products, then partition each corresponding bound weight into `J` and `K`; apply the spec's conservative ratios. Never assume posterior risk monotonic in detector efficiency.
- [x] **Step 4: Rerun suites with independent numerical refinement.** Compare to tighter split integration/high precision, targeting `1e-8` absolute and `1e-6` relative above `1e-6`; assert validated main-cell error `<1e-4`. Tiny interval-nuisance enumeration must lie inside reported outer risks. Expected: PASS with recorded error evidence; an internal quadrature error estimate alone cannot pass.
- [x] **Step 5: Commit.** `git commit -m "feat: add matched finite-site integration and silence controls"` after staging oracle/contracts/tests.

## Task 8: Independently check the finite-age theorem formulas

**Files:** Create `src/seti_audit/theorem.py`, `tests/test_theorem.py`; expose the deterministic portion of `theorem-check` in `cli.py`.

**Interfaces:**

- `finite_age_kernel(q:float,h:float,T:float,d:int) -> float`.
- `continuum_mean(h:float,alpha:float,T:float=1,d:int=3,intensity:float=1) -> float`, where `intensity=lambda*nu_d*c**d`.
- `warning_intensity(h:float,u:float,alpha:float,T:float=1,d:int=3,intensity:float=1) -> float` implements the independently repaired `L`.
- `free_joint_cdf(h:float,z:float,u:float,alpha:float) -> float` integrates `exp(-b(x))*L(x,u)/(1-exp(-b(h)))` through `zh`; tiny atomic-law adapters are private reference helpers.

- [x] **Step 1: Write failing mathematical tests.** Assert both kernel branches agree at `q=h/T`; direct radial integral agrees relatively within `1e-9` at ordinary scale. For alpha 1 and 2 assert `b=.75*h**2+.5*h**3` and `b=h**3-.25*h**4` at `.001,.1,.5`. Verify `b'(h)=L(h,1)`, `L(h,0)=0`, joint CDF endpoints and distinction between conditioning on `H=h` and `H<=h`. An atomic speed exactly at the split must be counted once; tiny `h` must not produce cancellation zeros. Assert alpha 3 is compared to logarithmic convergence rather than a false finite-h `1e-9` limiting error.
- [x] **Step 2: Run `tests/test_theorem.py` through the logging wrapper.** Expected: FAIL for missing stable formulas.
- [x] **Step 3: Implement blueprint §§3.3,8.2 formulas.** Split quadrature, normalize tiny powers, use `log1p/expm1`, and use mpmath on the small precision-sensitive subset. Record source equations versus independent repair. Run the six alpha values and four binary64 horizons; enable `1e-12` only after high-precision convergence. Do not claim reproduction of absent source scripts.
- [x] **Step 4: Rerun tests and the deterministic `theorem-check` mode.** Expected: PASS with source hash, exact/leading ratios, warning/derivative checks, precision, and tolerances saved under `results/theorem/`; no assertion that continuum asymptotics describe the stellar catalog.
- [x] **Step 5: Commit.** `git commit -m "feat: verify finite-age contact and warning formulas"` after staging theorem/CLI/tests and small verification artifacts.

## Task 9: Validate accepted growth in the finite continuum shell

**Files:** Modify `theorem.py`, `cli.py`; create `tests/test_shell.py`; extend `contracts.py` with `ShellSummary`.

**Interfaces:** `sample_shell(config:dict,rng:Generator,n_histories:int,ledger:ResourceLedger) -> ShellSummary`, with config fixed to alpha 1 and `h=.02` or `.5`. `ShellSummary` records conditional trial/accepted-contact counts, free and accepted normalized warnings, censoring, b/s, and resource use; the inference/report layers calculate intervals later.

- [x] **Step 1: Write failing shell controls.** Assert positive-truncated Poisson probabilities start at `b/expm1(b)` and follow the exact recurrence; reject `b=0`. On forced deterministic points assert the contact winner can change/be suppressed while earliest signal is unchanged. Assert an arrival beyond `T+h` is right-censored and never called the global later arrival. Finite free samples are compared to Task 8 `free_joint_cdf`, not the exact-arrival conditional CDF.
- [x] **Step 2: Run `tests/test_shell.py` through the logging wrapper.** Expected: FAIL for absent shell construction.
- [x] **Step 3: Implement the finite-shell sampler in blueprint §8.2.** Sample independent restrictions to `B_h` and its complement, continuous geometry, and chronological suppression. Recompute ambiguous count-CDF sums at high precision. Start with 10k conditional histories per reference horizon and extend at frozen precision checkpoints when needed. If other horizons/alphas become necessary, derive and verify a suitable sampler. Do not impose a sample ceiling or apply the stellar first-clock reduction to continuum points.
- [x] **Step 4: Rerun tests and a tiny development sample.** Expected: PASS; diagnostic intervals for `(1-exp(-b))*P(accepted contact|N_B>=1)` agree with rigorous bounds at their declared error level. Deterministic phantoms must exercise suppression even when the random sample does not. Task 14 completes any needed confirmation/reference precision; keep development and confirmation evidence distinct.
- [x] **Step 5: Commit.** `git commit -m "feat: add bounded continuum suppression reference"` after staging the shell implementation/tests.

## Task 10: Certify compatibility, risks, and family envelopes

**Files:** Create `src/seti_audit/inference.py`, `tests/test_inference.py`, `tests/test_envelopes.py`; extend `contracts.py`.

**Interfaces:**

- `AuditCounts(histories:int,arrivals:int,nulls:int,arrival_nulls:int,sum_w:float,sum_bw:float,bound_counts:dict[str,int])`; count keys for bounded weights are `null_low,null_high,J_low,J_high,K_low,K_high`, all with denominator `histories`. Track actual attempted universes separately in batch/resource records.
- `accumulate(arrival_flags:NDArray[np.bool_],weights:FloatArray,uniforms:FloatArray) -> AuditCounts`; bounded variant `accumulate_bounds(arrival_flags,low_weights,high_weights,uniforms) -> AuditCounts` uses the same shapes/types.
- `exact_interval(successes:int,trials:int,alpha:float) -> WeightBounds`; `alpha_at_checkpoint(pool_error:float,registry_size:int,checkpoint_index:int) -> float` returns `A/(M*j*(j+1))`; `summarize(counts_by_cell:dict[str,AuditCounts],protocol_lock:dict,checkpoint_indices:dict[str,int]) -> Summary`, with indices keyed by unique interval-registry item. `Summary` holds rows, certified/possible model sets, envelopes, and claim certificates.
- `certify_narrowing(baseline_upper:WeightBounds,post_upper:WeightBounds,has_certified_retained:bool) -> str` returns `material`, `nonmaterial`, or `inconclusive`; `summarize` handles incompatible families first. `baseline_upper` bounds the original family's maximum R0. `post_upper.low` is the maximum risk lower bound among certified-retained cells (zero if none); `post_upper.high` is the maximum risk upper bound among all possibly retained cells. These distinct sets are essential to the positive/negative rules.

- [x] **Step 1: Write failing inference controls.** Use exact two-branch weights to assert `R0=.5,likelihood=.53,R=.5/.53` for fast/dark and `R=.03/.53` for the positive control. `test_zero_null_draws` asserts risk `[0,1]`; zero arrivals with `n>0` asserts upper bound `>0`; weighted noninteger successes must fail. `test_threshold_equality` asserts retention at `.05` and exclusion only below it. `test_interval_partition_bounds` enumerates nuisance weights and asserts every risk lies in `J-/(J-+K+)` through `J+/(J++K-)`.
- [x] **Step 2: Run `tests/test_inference.py tests/test_envelopes.py` through the logging wrapper.** Expected: FAIL for missing estimates/certificates.
- [x] **Step 3: Implement point estimates and checkpoint-valid intervals.** Use integer audit counts, the frozen registry with `alpha=A/(M*j*(j+1))`, and open-interval independent-per-history uniforms paired across variants. Merge numerical error conservatively. Mixed-speed C uses separate proposal-diagnostic checkpoint intervals times `C_star`; independent cells use quadrature evidence. No weighted-count binomial intervals or survivor-stopped proposal ratios. Zero total weight produces an explicit undefined point estimate and conservative interval, never NaN or zero.
- [x] **Step 4: Add and pass adversarial envelope tests.** An unresolved high-risk cell contributes `[0,1]` and blocks a false positive; an empty possible set is incompatible, never risk zero; `L0=0` blocks relative certification; failure to prove positive stays inconclusive unless the spec §3 negative inequality certifies nonmateriality. A certified retained lower post bound rules out narrowing when either maximum possible contraction is strictly below `.01` or `.25`. Invisible counterparts retain original demographic risks; threshold reuse never triples error allocation. Test open-uniform endpoints, zero total weighted denominator, and zero binomial trials explicitly. Test `alpha_at_checkpoint(.025,M,j)` directly and the telescoping cumulative allocation across all looks; reusing thresholds does not allocate again. Expected: both suites PASS, including every Review Focus uncertainty case.
- [x] **Step 5: Commit.** `git commit -m "feat: certify null compatibility and arrival envelopes"` after staging inference/contracts/tests.

## Task 11: Pass correctness, then improve batching and plan precision

**Files:** Modify `model.py`, `cli.py`; create `src/seti_audit/experiments.py`, `tests/test_batch.py`, `tests/test_calibration.py`; extend `contracts.py` with batch representations.

**Interfaces:**

- `ClockBatch` carries Task 4 clock arrays with shape `(batch,n)`; `HistoryBatch` carries site-indexed candidate arrays, accepted masks, occupation arrays, per-history arrival/censoring arrays, and sparse diagnostics. `simulate_batch(clocks:ClockBatch,geometry:Geometry,intersite:bool=True) -> HistoryBatch`; `history_at(batch:HistoryBatch,index:int) -> History` supplies deterministic replay samples. Scalar engine remains the oracle.
- `CalibrationResult(initial_survivors:dict[int,int],initial_diagnostic_proposals:dict[int,int],logical_batch_size:int,projected_seconds:float,proposal_costs:dict[int,float],acceptance_bounds:dict[int,WeightBounds],timings:dict,rss_bytes:int,execution_recommendations:tuple[str,...],evidence_ids:tuple[str,...])`; `calibrate(protocol:Protocol,catalog:Catalog,schedule:Schedule,ledger:ResourceLedger) -> CalibrationResult`. Precision analysis sets initial checkpoints; runtime estimates guide optimization, not a stop flag.
- `PilotResult(passed:bool,evidence_ids:tuple[str,...],controls:dict,diagnostics:dict)`; `pilot(protocol:Protocol,catalog:Catalog,schedule:Schedule,ledger:ResourceLedger) -> PilotResult` returns exact-control validation and descriptive mechanism diagnostics; never edits scientific values. Expose `calibrate --config` and `pilot --config`.

- [ ] **Step 1: Write failing batch/projection tests.** Assert pathwise scalar/batch equality for identical clocks, including phantoms, ties, suppressed cases, and partial batches. A very slow cost projection must preserve the required matrix/precision and recommend scheduling or optimization, never a 25k downgrade or automatic infeasibility. Physical memory pressure changes microbatch size while preserving draws/precision. Pilot risks never retune the scientific grid, checkpoint policy, or thresholds.
- [ ] **Step 2: Run the new suites through the logging wrapper.** Expected: new behavior FAIL; existing scientific controls remain passing. Diagnose and repair actual G1 failures and revalidate affected work until trustworthy; no repair count or elapsed-time allowance ends this task.
- [ ] **Step 3: Implement rank-wise NumPy propagation and measured projections.** Avoid `(batch,n,n)` arrays. Begin with 1024/4096/appropriate 16384 attempts at low/high rates, S1/S3/S4, and S4 age cases; compare cold and repeated warm work. Include imports, clocks, propagation, linked selection, quadrature, replays, diagnostics, and reporting. Use conservative survival-acceptance bounds in cost projections. Improve inefficient paths when useful and independently validate any accelerator or estimator change; retain binary64 and the full scientific family.
- [ ] **Step 4: Pass the full tiny-control suite, then execute G2/G3.** Expected: exact G1 invariants pass and performance measurements support an execution strategy for the precision needed. Pilot development cases `mu=1/S1` and `mu=12/S4` plus positive/null/sign and shell controls. Set initial samples from spec §8 and numerical resolution, allowing larger initial checkpoints where needed; neither slow cost nor a launch count closes the project. Use phase-0 seeds and record all improvements and tests.
- [ ] **Step 5: Commit.** `git commit -m "perf: validate batched histories and measured feasibility"` after staging code/tests and small G1–G3 evidence with source/config hashes.

## Task 12: Freeze the finite matrix and implement exactly resumable confirmation

**Files:** Modify `experiments.py`, `artifacts.py`, `resources.py`, `cli.py`, `contracts.py`; create `tests/test_matrix.py`, `tests/test_runner.py`, `tests/test_resume.py`, `tests/test_freeze.py`.

**Interfaces:**

- `build_matrix(protocol:Protocol,schedule:Schedule) -> tuple[dict,...]` produces unique cells with stable IDs, model kind, family membership, emission/detector/continuation IDs, and evidence grades.
- `build_bound_registry(cells:tuple[dict,...]) -> dict` enumerates unique interval items and their primary/diagnostic pool. Record `A`, `M`, and `alpha=A/(M*j*(j+1))` for checkpoint `j`, covering all future predeclared precision checkpoints. Identical shared intervals have one ID, reused across thresholds.
- `freeze_protocol(protocol:Protocol,catalog:Catalog,schedule:Schedule,calibration:CalibrationResult,pilot:PilotResult,output_dir:Path) -> dict` writes immutable `results/protocol.lock.json`, `matrix.json`, and `bound_registry.json` with mutually validated hashes.
- `run_confirmation(protocol_lock:dict,resume:bool,ledger:ResourceLedger) -> dict`; `commit_batch(output_dir:Path,batch_id:str,payload:dict,arrays:dict) -> str`; `load_committed_batches(output_dir:Path,protocol_hash:str) -> tuple[dict,...]`.
- Expose `freeze --config`, `run --protocol`, and `run --protocol ... --resume`. Errors use exit 2 for invalid config/lock, 3 for blocking input, 4 for invalid correctness, 5 for an actual physical resource interruption with resumable work. Reached-grade success is 0 with machine-readable limitations; an interruption never implies completed research.

- [ ] **Step 1: Write failing matrix/freeze tests.** Assert 16 primary plus four age demographics, 16 ideal settings, exactly the spec §4 combinations, and no accidental future E2–E5 Cartesian expansion. No reporting-cell quota may omit required rows. Three tau statuses share each cell. Pool allocations across all items/checkpoints remain at most `.025` each. Missing correctness/precision-policy evidence, altered source hashes, outcome-based grid changes, or unsupported exact-schedule claims block scientific confirmation; slow runtime projections do not.
- [ ] **Step 2: Run the four suites through the logging wrapper.** Expected: FAIL for missing lock, matrix, and durable batching.
- [ ] **Step 3: Implement stable IDs, seed streams, and locked precision policy.** Primary model IDs `0..15` iterate mu then S1–S4; diagnostics `16..19` iterate ages then S1/S4. Use `Generator(PCG64(SeedSequence([20261101,phase,stage_id,model_id,purpose_id,batch_id])))`, separating development/confirmation phases. Freeze purpose IDs, logical batch boundaries, initial cumulative sample sizes, doubling sequence, and interval registry/error policy. Physical microbatching may change with pathwise equality and unchanged draws. Variants share history uniforms; independent histories do not.
- [ ] **Step 4: Implement extendable confirmation and durable resume.** Advance required settings fairly, with independent proposal-count diagnostics and survivor draws. Complete cumulative checkpoints `n_j=n_1*2**(j-1)`, then evaluate checkpoint-adjusted intervals to continue unresolved precision work. There is no maximum duration, attempt count, or checkpoint. Log work, stage hashed batch payloads, publish atomically, and append one commit record per batch. Recover valid orphan batches by identity, preserve interrupted usage, and reject changed locks, duplicate/conflicting IDs, or corrupted counts. Retain all prior evidence and earlier valid checkpoints; an incomplete checkpoint remains pending until resumed. Never reseed or discard unfavorable evidence. A proof may discharge only its own claim; missing evidence does not delete other required comparisons.
- [ ] **Step 5: Pass fault-injection and precision-extension suites.** Crashes around publication/manifest commit must resume to identical counts and seed identities without duplicate batches or lost usage. Test an interruption mid-C-diagnostic and mid-checkpoint, a restart after a valid checkpoint with further precision pending, and an extension that preserves old counts/lock while reducing interval error per the frozen formula. Simulate duration/proposal/launch counters beyond former limits and assert work continues. Reject simultaneous writers, corruption, and mismatched dependency identity. Expected: all four suites PASS on tiny synthetic runs.
- [ ] **Step 6: Commit.** `git commit -m "feat: freeze scientific protocol and resume evidence safely"` after staging runner/storage/CLI/contracts/tests.

## Task 13: Produce evidence-only reports and a complete offline smoke path

**Files:** Create `src/seti_audit/reporting.py`, `tests/test_reporting.py`, `tests/test_cli.py`; modify `cli.py`, `README.md`, `.gitignore`; add tiny complete/blocked/invalid result fixtures under `tests/fixtures/`.

**Interfaces:**

- `render_report(results_dir:Path,output_dir:Path) -> dict` validates and reads saved protocol, results, provenance, numerical evidence, and failures; returns paths/hashes for tables, figures, report, and conclusions. No RNG or network access.
- `run_smoke(protocol:Protocol,output_dir:Path,ledger:ResourceLedger) -> dict` uses one explicitly synthetic history, linked weight, Bernoulli interval, and report row. Expose `smoke --config` and `report --protocol [--from-results]`; both report forms only consume saved evidence.
- Row schema: `cell_id,family_ids,model_kind,model_id,k,emission_id,detector_id,schedule_grade,detector_grade,C,likelihood,R0,R,intervals,numerical_errors,compatibility,attempted,surviving,nulls,arrivals,checkpoint_ids,completion_status,failure_ids,evidence_ids,protocol_hash`. `conclusions.json` contains `claim_id,claim,outcome_category,scope,evidence_ids,unresolved_dependencies` for each claim.

- [ ] **Step 1: Write failing report/CLI tests.** Patch acquisition and RNG entry points to raise during regeneration; a valid report still succeeds. Assert a missing mandatory result remains an unresolved row and outer-envelope contributor; a blocked calibration remains F2; a fully excluded family has null risk/status rather than zero. Assert all five outcome categories are representable per claim, each conclusion's evidence IDs resolve, and synthetic fixture rows are visibly synthetic. A theorem failure can coexist with independently validated finite-site claims.
- [ ] **Step 2: Run `tests/test_reporting.py tests/test_cli.py` through the logging wrapper.** Expected: FAIL for absent report/smoke behavior.
- [ ] **Step 3: Implement reports and reproduction instructions.** Render the spec §10 report contents and four required static figure families, or justified table substitutes; label model families, uncertainty, data grade, and source/configuration IDs. Preserve signed risk increases and distinguish weighted estimates from certified intervals. Emit explicit null/status for undefined values and list every unperformed validation. Document setup, every supported CLI command, evidence limitations, source hashes, checkpoint/error allocation, ledger/resume behavior, and `report --from-results`. Analytically resolved or genuinely blocked components receive an honest evidence report while every unaffected required component continues.
- [ ] **Step 4: Pass green end-to-end suites.** In an isolated temp project, verify installed package dispatch, all required subcommand parsers, a complete smoke path with runtime recorded and no time deadline, deterministic pause/resume, and two evidence-only report regenerations with identical table/conclusion contents. Check finite JSON, CSV schema, artifact links/hashes, missing-file error classification, actual memory/disk preflight, and the attained-grade README. Expected: both suites PASS; include setup/import/report usage once in the ledger.
- [ ] **Step 5: Commit.** `git commit -m "feat: report scoped research evidence and reproduction paths"` after staging reporting/CLI/docs/tests.

## Task 14: Complete the required research and evidence report

**Files/artifacts:** Produce the frozen protocol/matrix/interval registry, immutable manifests/checkpoints/aggregates, resource/failure/deviation records, evidence tables, `conclusions.json`, `report/REPORT.md`, figures, and final `README.md`. Preserve the Task 2–3 inputs and provenance. Stream/compress artifacts to fit actual available storage; retain aggregate evidence and replay samples instead of every trajectory.

**Interfaces:** Consume Task 12 frozen runner and Task 13 report renderer. This is execution of the research, not another software feature; reuse the validated tests instead of writing implementation-mirroring tests.

- [ ] **Step 1: Establish G0–G3 validity and resolve recoverable obstacles.** Reuse valid acquisition, correctness, performance, and pilot evidence without resetting records. Repair defects and pursue ordinary data recovery; F1/F2 permit unaffected conditional work. Any genuine missing geometry/calibration/schedule or physical resource obstacle is documented specifically while independent work continues. A scientific change needs a dated deviation and independent fresh confirmation; computationally reducible uncertainty remains work, not an early completion category.
- [ ] **Step 2: Freeze scientific choices and complete G4.** Run `python -m seti_audit freeze --config config/protocol.json` and `python -m seti_audit run --protocol results/protocol.lock.json`. Expected: complete scientific matrix, source grades/hashes, initial samples and extension/error scheme, independent C diagnostics, and fresh phase-1 primary evidence. Resume operational interruptions with the same lock. Continue scheduled precision checkpoints until the primary claim has defensible support; preserve all negative/favorable histories and all model cells.
- [ ] **Step 3: Complete every required G5 comparison.** Reuse prefixes for E1/E0 futures, complete all age diagnostics, ideal-silence/future references, detector/emission sensitivities, repeated-visit dependence and continuous Dpositive/F1 bounds, and reference checks. Extend their precision as needed using the frozen scheme. No stage duration or workload quota excuses an unfinished mandatory sensitivity. The analytic E0/Duncal obstruction avoids redundant work for those claims while the bright-family audit and its robustness continue.
- [ ] **Step 4: Validate and regenerate the final evidence in G6.** Run `python -m seti_audit report --protocol results/protocol.lock.json --from-results`; for an independently resolved or genuinely blocked pre-freeze component, render its evidence with saved configuration/provenance and no invented lock. Repeat all three blueprint §13 review passes. Verify checkpoint-wise error accounting, positive/negative certificates, full required matrix, unresolved-cell inclusion, F1/F2 wording, all resource/failure records, and report regeneration. Supply actual findings and identify irreducible empirical limitations; elapsed time alone supports no completion/infeasibility claim.
- [ ] **Step 5: Commit the research result.** Stage small configs/hashes, aggregates, failures, tables/conclusions/report/figures and final usage; check the staged diff for bulk archives or secrets. `git commit -m "research: record completed SETI null audit and evidence limits"`. State completed findings, uncertainty, validation, genuine unresolved dependencies, and measured costs. Do not mark the project complete with outstanding recoverable calculations or required validation merely because it has taken longer than expected.

## Coverage and plan review

| Specification requirement | Owning tasks / decisive evidence |
|---|---|
| §1 source authority and source/derivation distinction | 1–3, 8, 13–14: revised blueprint hash, unchanged PDF, and evidence labels |
| §2 scope, exclusions, staged approach | 3, 11–14: explicit grades/gates; no smaller scientific grid |
| §3 quantities, compatibility, material/negative/invisible rules | 10: exact updating controls, empty/unresolved sets, conservative certificates |
| §4 complete finite matrix and continuations | 1, 5, 12: config/matrix counts, shared prefixes, no accidental Cartesian claims |
| §5 catalog, schedule, acquisition and fallback | 2–3: identity, signed coordinates, completeness, streamed hash, F1/F2 |
| §6 scalar semantics and exact survival | 4–5: phantoms, finite enumeration, lower-cone sampling, future invariance |
| §6 linked selection and bounded response | 6: shared status, CTMC, temporal/frequency gates, enumerated nuisance coverage |
| §6 matched independent/ideal controls | 7: unconditional-clock quadrature, own survival, atom, exact silence gap |
| §6 continuum reference and source repair | 8–9: radial/closed-form/high-precision checks, atomic endpoints, shell censoring |
| §7 numerical/statistical assurance | 7–10, 12: refinements, integer intervals, frozen registry with checkpoint error allocation, independent proposal diagnostics |
| §8 resource use, seeds, freeze, failures/resume | 1, 3, 11–12, 14: observational accounting, optimization, valid precision extensions, interruption tests |
| §9 package/artifact/CLI contracts | 1–13: typed interfaces, parser/smoke tests, complete safe artifacts |
| §10 completion and report | 3, 11, 13–14: completed comparisons, evidence-only regeneration, demonstrated limits per claim |
| §11 design review | Recorded in approved spec; this plan receives the author's coverage/interface review |

Author self-review covers specification coverage, shared contracts, task verification, the five Review Focus cases, and proportion. The user-directed revision removes artificial execution/repair/sample quotas, replaces budget enforcement with observational resource logging, and permits precision extensions with simultaneous checkpoint-valid uncertainty. Completed evidence and genuine empirical limitations govern closure; an operational interruption leaves work pending. Implementation checkboxes remain unchecked until the work actually completes.

Implementation handoff requires a separate user instruction. Both Superpowers execution methods remain available; keep the approved current-branch constraint. Native execution avoids repeated context handoffs across these tightly shared scientific interfaces; subagent-driven execution adds an independent review per task at greater context cost. Neither implementation nor research execution is authorized merely by approval to write this plan.
