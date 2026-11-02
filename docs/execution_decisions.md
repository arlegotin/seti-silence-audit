# Execution decisions

Chronological rulings made during inline execution on the requested current branch. Each entry records its cost if wrong. Final review findings and dispositions are recorded separately.

1. Ruling: Execute inline on current main branch — user explicitly requested the current branch; this overrides default worktree isolation — cost if wrong: commits modify the current local branch, as requested.

2. Ruling: Use native Python 3.12 in .venv — available alongside system Python 3.14, matches the blueprint's preferred version and avoids global changes — cost if wrong: reproduce with the recorded dependency lock.

3. Task 3: Ruling: Split HTTP/stream/source checks into acquisition.py and re-export the public input contracts from data.py — keeps geometry/timing independent of network transport — cost if wrong: one extra module boundary, with integration tests.

4. Task 4: Ruling: Treat stored q as the authoritative speed mark and use stable q-based travel times; retain float v for display/validation — avoids introducing a light-speed atom or losing sub-ulp warning gaps — cost if wrong: callers that reconstruct events from rounded v instead of q can disagree, so all model consumers must preserve q.

5. Task 5: Ruling: Keep scalar conditional sampling pure and return its attempt count instead of an unused ResourceLedger argument — diagnostics/replays already return counts and the batch owner records them, avoiding per-universe fsync — cost if wrong: a caller could omit count aggregation; Task 12 must test durable batch accounting.

6. Task 11: Ruling: Measure report serialization primitives now and measure complete report rendering after Task 13 supplies it — the plan requested timing a later producer before it exists; avoid invented timing — cost if wrong: the initial runtime projection omits full report-rendering overhead, which must be recorded in Task 13.

7. Task 12: Ruling: Isolate immutable batch storage in storage.py and resumable orchestration in runner.py, re-exporting the planned public contracts from artifacts.py and experiments.py — separates durable I/O from scientific estimators — cost if wrong: extra module boundaries, covered by direct publication and end-to-end resume tests.

8. Task 12: Ruling: Under F1, tag the same survey-weight enclosure as covering both nominal and dependence-robust repeated visits instead of rerunning identical bounds — F1 already uses maximum-marginal/capped-sum bounds without visit independence — cost if wrong: could hide a distinct dependence assumption; scalar/accelerated F1 implementations and the final review must verify the shared enclosure covers both.

9. Task 13: Ruling: Add a check CLI that emits complete-suite readiness evidence — research freeze needs reproducible G1 hashes, and selected development tests cannot certify research — cost if wrong: one extra CLI/API contract, covered by selected/full gate tests.

10. Task 14: Ruling: Replace computationally loose full-range Dpositive and near-threshold Dweak precision work with contiguous shared-efficiency subdomains and fresh stage-8 confirmation — the original valid outer enclosure reached ~.40 and further MC sampling cannot cure its unattainability; complete the already prescribed original look and retain every batch before transitioning — cost if wrong: a second estimator and reproducibility surface need independent controls and review; no scientific grid or thresholds change.

11. Task 14: Ruling: Fund the new confirmation only from 12 analytically zero-noncoverage ideal-S1 interval allocations, A_ref=.025*12/2536 — the nearest-star 277.102-year gap makes all their century-arrival risks exactly zero, and their CP intervals always contain zero. The original nonzero-error events plus refinement remain within .05. Reject data-dependent reclamation of unused checkpoint tails — cost if wrong: validity depends on the hard-gap proof, explicit donor IDs, unique parent counting and subdivision/checkpoint allocation; these receive tests and final review.

12. Task 14: Ruling: Tighten all 52 matched interacting baselines using their unweighted flags at the same completed fresh checkpoints, funded only by two disjoint mathematically certain free-shell CDF endpoint allocations — baseline precision, rather than the remaining radio estimate alone, limited the k=10 comparison; alpha=A_base/[52*j*(j+1)] covers all fixed quantities/looks and needs no independence from null audits — cost if wrong: depends on the endpoint-support proof and complete fixed-checkpoint counts; policy, counts, source hashes, exact intervals and intersections are validated and retained.

13. Task 14: Ruling: Report cumulative history counters as instrumented science/calibration/pilot/replay work, with an explicit historical-unit-test-count limitation — old uninstrumented unit calls cannot be reconstructed exactly without invented records, while all test durations and all committed scientific work are retained — cost if wrong: undercounts total historical engineering simulation calls; no hardware-speedup, resource-infeasibility or scientific-inference claim uses an exhaustive engineering-work count.
