# SETI silence audit: research and software specification

Date: 2026-11-02. Status: initial design builder checked and approved; amended on 2026-11-02 under the user’s instruction to prioritize substantive results and remove artificial execution caps.

## 1. Intent and authority

Build the reproducible finite-target research audit described in [the blueprint](../../blueprint.md), answering whether the UCLA 2020–2023 radio null materially narrows century-arrival probabilities within its declared model families. The audience is a researcher inspecting the assumptions and an engineer reproducing the calculation. A verified information limit or certified negative result is a useful outcome. Complete the required comparisons, robustness work, and validation; an elapsed duration or arbitrary workload count never completes the project.

This specification makes the blueprint implementable; it does not replace its scientific protocol. The blueprint remains normative for equations, source references R1–R14, the target transcription, acquisition hashes, and the experiment matrix. Any apparent conflict must be recorded and resolved before confirmation; never silently choose the more favorable interpretation.

The PDF remains unchanged. The blueprint was revised on 2026-11-02 to remove artificial execution caps; its current content hash is recorded below. The original inputs remain recoverable from commit `6a556dc`.

| Source | SHA-256 | Use |
|---|---|---|
| `docs/blueprint.md` | `b1b7db71cb41c69f6f508a3010b11ae5fc1168adcc8ae9bbb646008d1daaa211` | Research requirements and inherited source-audit claims |
| `docs/silence_contact_theorem.pdf` | `2a6c071a3edfc6ff3dc5db07ac4c94448537f907e9e22051f9397b49374839fe` | Mathematical reference; 14 pages |

For this design, the PDF was read through text extraction and page 8 was visually inspected. Its warning display is visibly incomplete. The repair in blueprint §3.3 is an independent derivation, not recovered source text. The source's claimed computation scripts are absent. Previous planning probes and literature inspections remain attributed to the blueprint; they are not results reproduced in this checkout. External source/data verification belongs to acquisition, not this documentation task.

## 2. Goals, exclusions, and approaches

Required goals:

- Separate demographic survival, compatibility with the radio null, and within-model updating.
- Preserve chronological birth suppression, shared physical sources across visits, and the survey's two-ON selection requirement.
- Compare interacting histories with deterministic independent-site quadrature and same-star ideal silence.
- Produce conservative numerical intervals and retain every unresolved model in outer envelopes.
- Complete the research with measured resource use, deterministic resume, and a report reproducible from saved aggregates; improve execution methods and precision as needed.

Excluded scope: Galactic forecasting, empirical priors on extraterrestrial behavior, anthropic sampling, front collisions or extinction, additional field stars, raw-voltage processing, arbitrary-signal calibration, a dashboard, databases, cloud compute, and historical priority claims. A smaller catalog or favorable grid chosen after seeing risks is unacceptable. So are synthetic data presented as observations, weighted counts presented as binomial trials, and a timeout presented as a negative result.

Approaches considered:

| Approach | Tradeoff | Disposition |
|---|---|---|
| One package, shared histories, staged evidence gates | Requires explicit contracts for conditioning and data grades; avoids duplicated scientific logic | Selected: directly implements the fixed blueprint |
| Independent theorem, simulator, and survey applications | Can develop separately, but duplicates conditioning, provenance, and numerical conventions | Keep mathematical code modular inside the package instead |
| Smaller empirical grid first, expand later | Cheaper initial run; cannot answer the blueprint's prespecified envelope question | Use synthetic controls and cost calibration only; retain the scientific grid |

The proposed engineering choices below are the author's calls, not prior user decisions: a Python package, standard-library CLI, typed dataclasses/NumPy arrays, JSON/CSV/NPZ artifacts, and narrow modules. The requested work stays on the current branch. This delivery produces a specification and plan; implementing or running the research is a subsequent task.

## 3. Scientific quantities and decision rules

Use light-years and Julian years, `c=1`, with zero at the actual final observing endpoint and horizon `h=100`. For an accepted history, let `A=min(b_i+r_i/v_i)`, `E={A>0}`, `B_event={0<A<=100}`, and `w=P(no verified detection | history)`. Use `age_years` in code to avoid confusing historical age with `B_event`.

Required per-model outputs are `C=P(E)`, `likelihood=E[w|E]`, `R0=P(B_event|E)`, and `R=E[1_B_event*w|E]/E[w|E]`. Also retain attempted, surviving, null, and arrival counts and numerical errors. `E` is stipulated, not established by the telescope. Do not penalize low `C` or add a population prior.

For each named, explicitly enumerated family report:

- `I0`: risks conditioned on `E` over the original family.
- `Iselect`: those pre-null risks restricted to compatible models.
- `Ipost`: null-conditioned risks over compatible models.

Compatibility thresholds are `tau in {0.01,0.05,0.10}`, with `0.05` primary. Retain when `likelihood>=tau`. With numerical intervals: certified retained iff `likelihood_low>=tau`; certified excluded iff `likelihood_high<tau`; otherwise unresolved. Equality at the threshold is retained. Display the certified-retained envelope and the outer envelope over all possibly retained cells. A missing/invalid cell contributes `[0,1]` unless an analytic bound narrows it. An entirely excluded family has no conditional risk, not risk zero.

Let `U0` and `Upost` be upper endpoints of `I0` and `Ipost`. Material narrowing requires both `U0-Upost>=0.01` and `(U0-Upost)/U0>=0.25`, certified conservatively from the lower bound on `U0` and upper bound on `Upost`. If the lower baseline bound is zero, do not certify a relative reduction. A negative requires the distinct upper-contraction test in blueprint §7.3 and at least one certified-retained model; lack of a positive certificate alone is inconclusive.

A null may increase `R`. The exact fast/dark control has `R0=.5`, `likelihood=.53`, `R=.5/.53`; the positive updating control has `R=.03/.53`. No optimizer, plot, or invariant may require `R<=R0`.

For every demographic model with a fully invisible counterpart, `w=1`, `likelihood=1`, and `R=R0`. Consequently the all-civilization post-null envelope contains the original demographic envelope. Duncal's allowed zero-response detector has the same obstruction. This does not prove an achievable `[0,1]` range and needs no large simulation.

## 4. Fixed model and finite workload

The complete parameter definitions in blueprint §§5 and 8.3 apply. Preserve stable integer IDs for every demographic and variant.

| Component | Required values |
|---|---|
| Geometry | 62 published rows, nominally 61 physical sites; merge TOI 1730.01's birthplace and link its visits, pending source reconciliation |
| Historical age | 10,000 years, with no preexisting expansion |
| Historical rates | Equal hazard `lambda_i=mu/(n*age_years)`; `mu in {0.1,1,3,12}` |
| S1 / S2 | Fixed `v=.1` / fixed `v=.5` |
| S3 | `.999` mass at `.1`; `.001` mass at `v=1/(1+U)`, `U~Uniform(0,1)` |
| S4 | `v=1/(1+U)`, `U~Uniform(0,1)` |
| Future rates | `k=1` primary; `k=0,10` continuation controls |
| Age diagnostics | Four ensembles: ages `{1000,100000}`, `mu=3`, S1/S4, `k=1`; hold `mu`, not current rate, fixed |
| E1 | `zeta=1`, immediate, persistent, always ON |
| E2 | `zeta=.1`, immediate, persistent, always ON |
| E3 / E4 | `zeta=1`; delay 100 years / radio lifetime 100 years |
| E5 | `zeta=1`; stationary ON fraction `.1`, correlation time 1 day; exact CTMC |
| E0 | Fully invisible analytic counterpart |
| Dnom / Dweak / Dhigh | Final-pair probabilities `.8836` / `.44` / `.94` |
| Dpositive / Duncal | Full-ON pair interval `[.44,.94]` / no positive final-response lower bound |

The primary comparison is E1/Dnom/age 10,000/`k=1` over 16 demographics. Evaluate E2–E5 and detector sensitivities on those histories. Continuation replays use E1 and analytic E0 only, with E1's three point detectors and interval bounds. Age diagnostics use E1, three point detectors, and matched independent-site controls. Same-star ideal silence uses the 16 primary demographics and all three continuations. These are one-factor sensitivities, not an unexecuted Cartesian robustness claim.

Pre-enumerate and hash the complete required reporting matrix before confirmation; there is no arbitrary reporting-cell quota. A cell is a model/observation variant, with all three threshold statuses stored together; thresholds are not independent simulations. Tag model kind (`interacting`, `independent_sites`, `ideal_silence`) and named family membership. Scientific additions require an explicit rationale and independent confirmation rather than outcome-driven grid changes. E0/Duncal obstructions and `mu=0` are analytic controls.

## 5. Input and observation contracts

### Catalog and provenance

Parse Appendix B without numeric coercion of TOI identifiers. Preserve all 62 source rows separately from the normalized physical sites; verify duplicate coordinates/distances and reject contradictory identities. Parse signed sexagesimal coordinates, including negative-zero declination. Convert parsecs with the exact expression in blueprint §6.1. Save radii and a 3D Euclidean distance matrix; angular separation alone is insufficient.

Retain the canonical PDF at `docs/silence_contact_theorem.pdf`; record its hash in the input manifest rather than making a second copy under `inputs/`. Keep downloaded small source documents and API metadata under `inputs/`, with origin, retrieval time, status, byte count, content hash, and evidence label. Inherited archive hashes remain expected hashes until streamed bytes are verified.

### Schedule grades and acquisition

Use the four published session dates and Dryad version 370211 specified in blueprint §2. Retry transient failures with appropriate backoff, diagnose persistent failures, and inspect alternative ordinary public or already-authorized routes when useful. A retry count or elapsed acquisition time does not establish unavailability. Stream candidate CSVs once, hashing original bytes and extracting unique observing metadata plus a small validation sample; never load the four-gigabyte archive into a dataframe. Verify both ON scans, pairing, chronology, duration, membership, repeated visits, and completeness including potentially absent zero-hit scans. A maximum candidate timestamp alone never establishes the exact endpoint.

Maintain separate status axes:

- `schedule_grade`: `exact`, `coarsened_F1`, or `unavailable`.
- `detector_grade`: `assumed_F2`, `unconstrained_F2`, or `calibrated` only with documented matching full-selection evidence.
- `source_status`: `source_verified` or `blueprint_transcription` for the geometry.

Exact `data/visits.csv` uses the blueprint §2.3 columns, with one row per ON scan and a shared `visit_id` for its pair. Set `t0=max(start_mjd+duration_s/86400)` only after completeness validation. Store time-scale assumptions. Convert relative day differences to years by dividing by `365.25`.

For F1, write `data/bounded_visits.json`, not invented exact scan timestamps. Each published row defines a visit with two nonoverlapping 150-second ON integrations, within the union of its group's permitted session intervals. Allow each session within 48 hours of the stated UTC midnight; endpoint interval is `[2023-05-13T00:00:00Z,2023-05-15T00:00:00Z]`. Subtract intervals with `[a,b]-[c,d]=[a-d,b-c]`, retain separate session alternatives, intersect with times at/before zero, and record this date interpretation as an assumption. Do not assign a year or a minute gap. If the original source/logs remain unavailable, report the inherited geometry transcription status explicitly.

Acquisition failure selects F1/F2 where defined and preserves all unaffected work. No substitute synthetic stars, authentication bypass, or autonomous contact with authors. A genuinely unrecoverable geometry is a blocker for empirical geometry claims; request only the smallest missing log/extract or calibration information in the eventual report.

## 6. Computational design

### Accepted histories and conditional sampling

Permanent occupation makes each site's first attempted birth sufficient: whether accepted or rejected, its site is occupied thereafter. Invert the piecewise cumulative hazard in blueprint §6.2, draw one speed mark, censor first attempts after 100, sort by `(birth_time,site_id)`, and accept only if `birth_time<occupation_time`. Accepted balls grow forever through overlaps; rejected sources never suppress or emit. Keep Earth arrival and signal time separate.

Implement a scalar reference before batching. A compact history carries accepted indices, birth times, speeds and `q`, earliest accepted arrival, occupation times, censoring, and replay diagnostics. A flagged boundary comparison triggers higher-precision re-evaluation, never an altered inequality. The flag tolerance is `max(1e-12 yr,64*machine_epsilon*max(1 yr,abs(relevant times)))`. `A=100` is included; `A=0` violates survival. Store `q` and count/bound any rounding safeguard that could introduce `v=1`.

Use the exact lower-support-speed cone proposal (§6.4), with `v_floor=.1` for S1/S3 and `.5` for S2/S4. Clock origins are `l_i=max(-age_years,-r_i/v_floor)`; invert `Lambda(l_i)+Exp(1)`, including the hazard offset. Filter only on accepted arrival. For common speeds, `C=C_star` exactly; mixed speeds need a separate proposal-count diagnostic, initially 50,000 proposals with predeclared precision extensions, and `C=C_star*acceptance_probability`. Never estimate `C` from the survivor-stopped sample with ordinary binomial intervals. Never restrict all candidates by their own marked hypothetical arrival.

Store unchanged pre-zero candidates, accepted fronts, and marks for future replays. Only sites with no attempted birth by zero receive a new residual exponential hazard; reuse it and its speed across `k=0,1,10`. Replay acceptance with the old fronts. Future changes must not alter `E`, `C`, or past likelihood.

Batch only after pathwise equality with the scalar reference. NumPy rank-wise occupation updates avoid a `batch*n*n` tensor. Batch size may fall to respect memory; star count and binary64 precision may not. Optional compiled acceleration requires a measured bottleneck, resource-use records, and pathwise validation. Improve or replace a sampler when needed, independently validating its estimator and uncertainty treatment.

### Linked selection likelihood

Each accepted source emits only at its original star. An ON scan at observer time `o` samples source time `o-r_i`; received emission is `[birth+delay+r_i,birth+delay+lifetime+r_i)`. Apply the same deterministic admissibility status throughout all visits. Primary bright families already condition on the frequency class and must not get another coverage multiplier. Any explicit diagnostic frequency mark must respect the exact mask in blueprint §5.2, zero-drift rejection, and full-track admissibility, including under Duncal.

Draw compatibility once per source. Integrate one shared source emission history across all its visits. Both complete ON integrations must be temporally eligible for point detectors and Dpositive. For E5 merge overlapping required windows, multiply `f*exp(-b*total_ON_duration)` by the exact `P11(gap)` factors; use consistent day/year units. Do not substitute independent duty-cycle draws.

For a set of source visits use the inclusion–exclusion formula in §6.5, preserving joint temporal probabilities. One visit gives `1-zeta*p*G1`; two give `1-zeta*(p1*G1+p2*G2-p1*p2*G12)`. Source independence and conditional recovery independence between visits are explicit model assumptions. Product source weights in log space, handle zero safely, and return one for no sources or no visits.

Also report dependence-robust repeated-visit weights: conditional detection lies between the largest marginal and the capped marginal sum; average compatibility once. Shared calibration parameters remain shared across sources. Do not independently integrate a different efficiency at every source.

F1 uses certain/impossible/uncertain full-window coverage and the explicit safe tests in §6.5. E5's unknown-gap activity lies in `[f^2*exp(-b*2d),f*exp(-b*2d)]`. Combine repeated-visit marginal bounds before source products. Dpositive endpoint evaluations bound weights, not posterior risk. Duncal permits partial-scan recovery as high as one when overlap is possible while keeping deterministic blind regions blind.

### Independent and ideal comparators

The independent-site oracle uses original unconditional first-clock densities plus the no-birth atom. Integrate speed out, then perform split one-dimensional birth-time quadrature for `e_i,h_i,n_i,j_i` (§6.6). Form `C=prod(e_i)`, `likelihood=prod(n_i/e_i)`, `R0=1-prod(h_i/e_i)`, and `R=1-prod(j_i/n_i)` in log space. It conditions on its own survival; interacting-survivor clocks must not enter this oracle. Validate with independent finite enumeration and low-rate Monte Carlo.

Same-star ideal silence has `P(S)=exp(-sum(lambda_i*(age_years-r_i)_+))`, conditional likelihood `P(S)/C`, and clocks starting at `max(-age_years,-r_i)` with the proper hazard offset. Sample directly. Label its difference from the real/coarsened survey as observation-model sensitivity. For a speed cutoff verify the exact gap `r_min*(1/v_max-1)`; continuum dimension does not impose an `h^4` law on these sites.

### Continuum reference

Implement the finite-age two-branch kernel and independently reconstructed warning expression in blueprint §3.3. Split at `q=h/T`, evaluate cancellation with `expm1/log1p`, preserve complementary atomic endpoints, and compare finite-horizon warning distributions with the integrated finite-horizon formula. Keep the contacting source's warning distinct from the global first signal.

Required checks: `d=3,T=c=1,lambda*nu3=1`, `alpha in {.5,1,2,3,4,6}`, `h in {1e-2,1e-4,1e-6,1e-8}`, and `1e-12` only with adequate arbitrary precision. Check direct radial integration, alpha 1/2 closed forms, `b'(h)=L(h,1)`, critical logarithmic convergence, a speed cutoff, and an atomic law. Ordinary-scale independent formulas agree relatively within `1e-9`; this is not a required convergence rate to an asymptotic limit.

The finite-shell experiment initially uses alpha 1, horizons `.02,.5`, and 10,000 histories per horizon, extended at predeclared checkpoints as needed to validate the reference. These sample counts are initial precision choices, not ceilings. Sample the positive-truncated Poisson directly and apply chronological suppression. Record arrivals outside the shell horizon as right-censored. Compare contact estimates to `b*exp(-s)<=p<=1-exp(-b)` and discrepancy `<=b*s`. Deterministic phantom cases must exercise rejection even if random runs see none. A defective reference theorem cannot validate the finite-site experiment, but does not by itself refute independently validated finite-site formulas.

## 7. Statistical and numerical assurance

One simulated universe is one independent unit. Save Rao–Blackwell weighted sums for point estimates and independent-per-history uniforms for integer Bernoulli audit counts. The same uniform may pair variants of that history. Compute exact Clopper–Pearson intervals from integer counts only; zero null histories gives risk `[0,1]`, and zero arrivals gives a positive upper bound unless analytically impossible.

Allocate familywise Monte Carlo error `0.025` to the primary decision and `0.025` to required diagnostics/robustness. Before confirmation enumerate and hash the unique scalar interval registry, assigning each item to one pool. For pool error `A`, `M` registry items, and checkpoint `j>=1`, allocate `alpha=A/(M*j*(j+1))` per item. Bonferroni over items and all checkpoints preserves the combined error at most `.05`, since `sum(1/(j*(j+1)), j>=1)=1`. Reuse shared intervals across thresholds without triple allocation. Report registry sizes, checkpoint indices, and per-checkpoint error. Calibration uncertainty is separate from Monte Carlo error.

For interval weights save Bernoulli counts for `J-`, `J+`, `K-`, `K+` and lower/upper null means. Bound risk by `J-/(J-+K+)` through `J+/(J++K-)`, inserting confidence endpoints conservatively. Undefined ratios become conservative endpoints 0 or 1. These are outer bounds and need not be simultaneously attainable. Include numerical error before making compatibility or narrowing claims.

Independent quadrature initially targets absolute probability error `1e-8` and relative `1e-6` for probabilities above `1e-6`. Independent refinements/high precision must show error below `1e-4` absolute for every main reporting cell and well below statistical uncertainty. An integrator's internal error estimate alone is insufficient.

Known-answer controls in blueprint §8.1 are release gates: zero births/dark emission, one-site clock, equal-speed pathwise equivalence, both deterministic fast-phantom cases, finite-support enumeration, lower-cone subset/sampling, linked duplicate visits, two-ON AND behavior, OFF-direction rejection, exact silence, cutoff gap, positive/sign-reversal updating, interval-nuisance coverage, and zero-count uncertainty.

## 8. Reproducibility, resource use, and completion

The following exact global constraints apply to the implementation and plan:

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

Inspect actual hardware and native Python at execution time. Target Python 3.12 or newer with NumPy, SciPy, Matplotlib, pytest, and mpmath; verify installed APIs/imports and freeze working versions rather than claiming availability now. Use standard-library argparse, CSV, JSON, urllib, hashing, datetime, and pathlib for orchestration and data.

G0 reconciles inputs and mathematical identities; G1 validates correctness; G2 measures performance and plans precision; G3 validates known mechanisms; G4 completes the primary comparison; G5 completes required robustness; G6 validates and reproduces the report. None has a time allocation or repair allowance. Begin performance measurements at 1024/4096/appropriate 16384 attempts with cold/warm comparisons, and extend measurements when needed. A slow estimate guides scheduling and optimization, never omission of a required model or automatic inconclusive completion.

Use fair tranches so difficult mixed-speed settings advance alongside other required cells. Initial sample sizes may be refined from precision analysis before confirmation. During confirmation, use the frozen cumulative checkpoint sequence and error allocation when deciding whether more precision is needed; maintain valid inference across all inspected checkpoints. Do not reset seeds, discard unfavorable prior evidence, or apply fixed-sample intervals repeatedly without the checkpoint adjustment. Preserve completed valid checkpoints and resume incomplete ones after an interruption.

Checkpoint atomic aggregate batches with protocol hash, stable batch ID, checkpoint index, RNG state/seed identity, counts, and cumulative resource usage. Resume verifies hashes and versions, never duplicates committed counts, and preserves all recorded work, including an interrupted job. Replayed future histories count as work in the record. Diagnose and repair fixable defects and independently revalidate affected evidence; neither repair counts nor elapsed time terminate the work. If missing data or a demonstrated mathematical/physical obstacle prevents one claim, identify it precisely and complete every unaffected calculation and required report.

## 9. Package and artifact boundaries

| Path | Responsibility |
|---|---|
| `pyproject.toml`, `requirements.lock.txt`, `README.md` | Installable package, verified environment, reproduction instructions |
| `config/protocol.json` | Versioned scientific defaults, precision checkpoints, and uncertainty allocation |
| `src/seti_audit/contracts.py` | Shared immutable config, catalog, schedule, history, counts, and result contracts |
| `src/seti_audit/data.py` | Source metadata, bounded streaming acquisition, identity reconciliation, schedule validation/F1 |
| `src/seti_audit/model.py` | Hazard inversion, marks, scalar/batched propagation, exact proposals, future replay |
| `src/seti_audit/detection.py` | Eligibility, shared-source CTMC/inclusion–exclusion, weight bounds |
| `src/seti_audit/oracles.py` | Independent quadrature, ideal-silence identities, tiny enumeration |
| `src/seti_audit/theorem.py` | Kernel, repaired warning, bounded shell reference |
| `src/seti_audit/inference.py` | Weighted estimates, integer intervals, family envelopes, decision certificates |
| `src/seti_audit/resources.py`, `artifacts.py` | Observational resource ledger and atomic, validated artifacts |
| `src/seti_audit/experiments.py` | Matrix, stable seed/batch IDs, gates, protocol freeze, confirmation/resume |
| `src/seti_audit/reporting.py` | Tables, static figures, claim records from saved evidence |
| `src/seti_audit/cli.py`, `__init__.py`, `__main__.py` | Thin command dispatch and public entry points |
| `tests/` | Exact controls, independently derived oracles, interruption and provenance tests |

Public contracts retain the blueprint's names: `load_catalog`, `load_schedule`, `sample_first_clocks`, `simulate_history`, `null_weight`, `independent_oracle`, and `summarize`. The implementation plan specifies their exact typed signatures and dependencies. Histories use compact arrays, not per-event object graphs in large batches.

Required saved artifacts are normalized `data/source_rows.csv`, `data/targets.csv`, exact visits or bounded visits, and `data/provenance.json`; input metadata under `inputs/`; `results/environment.json`, `protocol.lock.json`, matrix and bound registry, append-only run/resource records, checkpoints, aggregate counts and timings, failures, tables, and `conclusions.json`; plus `report/REPORT.md` and exportable figures. No dump of every successful trajectory. Retain small deterministic replay samples and representative failures.

The result-row schema must include `cell_id`, family/model IDs, schedule/detector grades, `C`, `likelihood`, `R0`, `R` with interval and numerical-error fields, compatibility at each threshold, attempted/surviving/null/arrival counts, completion status, failure/evidence IDs, and protocol hash. `conclusions.json` records each claim's category, scope, supporting evidence IDs, and unresolved dependencies. Represent absent/undefined estimates as explicit null/status fields; JSON must not serialize NaN or infinity.

Required CLI interfaces, to be implemented and verified later:

```text
python -m seti_audit env --out results/environment.json
python -m seti_audit acquire --config config/protocol.json
python -m seti_audit validate-data --config config/protocol.json
python -m seti_audit smoke --config config/protocol.json
python -m seti_audit theorem-check --config config/protocol.json
python -m seti_audit calibrate --config config/protocol.json
python -m seti_audit pilot --config config/protocol.json
python -m seti_audit freeze --config config/protocol.json
python -m seti_audit run --protocol results/protocol.lock.json
python -m seti_audit run --protocol results/protocol.lock.json --resume
python -m seti_audit report --protocol results/protocol.lock.json --from-results
```

`smoke` completes one synthetic history, linked likelihood, interval, and report row, recording its runtime without a time deadline. Its synthetic provenance is explicit. Report regeneration never simulates or fetches data. CLI failures distinguish unavailable input, invalid experiment, actual resource interruption, and invalid configuration, preserving artifacts and resumable work.

## 10. Acceptance and handoff

Before claiming implementation complete, pass the tiny mathematical gates, source/data checks for the attained grade, and end-to-end smoke/resume/report tests. Repeat the blueprint §13 mathematics, experimental, and execution reviews. Report what was actually checked; no test suite or experiment is implied to exist by this specification.

The final research report leads with the decision and evidence grade; includes the actual/interval endpoint, catalog reconciliation, assumption ledger, theorem repair and performed checks, all model rows and envelopes, interaction/ideal comparisons, continuation/age sensitivity, costs/failures, and at most one useful next step. Required figures are family risk envelopes, likelihood versus risk with thresholds, ideal-survey discrepancy, and exact/leading theorem ratios; use tables if few values are resolved.

Every claim receives one supported category: supported contribution, informative negative result, practical infeasibility, inconclusive evidence, or invalid experiment. Distinct claims may have different categories. A source access failure does not erase unaffected math; a theorem-reference defect does not automatically invalidate independent finite-site formulas; unresolved mandatory robustness limits the claim. A proof can discharge the particular claim it resolves, while all remaining comparisons and robustness work continue. Practical infeasibility requires a measured physical resource or algorithmic obstacle after documented remedies. Inconclusive evidence requires a specific empirical or identification limitation; computationally reducible uncertainty calls for further work. A resumable interruption is unfinished execution.

The only data gates left for execution are verified schedule completeness, a defensible full-selection calibration bridge, and actual machine feasibility. They have explicit fallbacks or remediation paths and do not impose time or workload deadlines. Builders may choose internal array layout, physically suitable batch sizes, validated computational methods, quadrature implementation, and plot styling while preserving these contracts. Scientific changes require an explicit deviation.

## 11. Design review record

A fresh scientific-software builder reviewed the initial specification and its delegated blueprint sections on 2026-11-02, before the user-directed removal of artificial execution caps. The reviewer found no important unanswered questions needed to produce an implementation plan. This checks design completeness, not implemented correctness or empirical validity.

Documentation checks confirmed source hashes, 62 transcribed rows and 61 distinct identifiers, matching duplicate geometry, six nominal sites within 100 light-years, local links, and Markdown whitespace/fence balance. The user then directed removal of artificial time and workload caps; the blueprint, specification, and plan were revised consistently, including uncertainty accounting for precision extensions. No survey acquisition, PoC implementation, or simulation was performed during this documentation task.
