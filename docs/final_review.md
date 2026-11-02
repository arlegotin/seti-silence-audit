# Independent review and verified fixes

The fresh whole-branch review covered `b3a8758..d21192c`, using
`gpt-6-astra` with high reasoning effort. The reviewer worked read-only and
dispatched no additional agents. Its verdict was **with fixes**: no Critical
findings, three Important findings, no deferred Minors, and no required
behavior declined for judgment. This document records the author's fix pass;
it does not claim a second independent review.

The reviewer independently passed 236 tests, reconstructed all 8,260
interacting refined subdomains from 41,304 integer interval records, checked
the confidence allocation mathematics for the fixed catalog, and reproduced
the saved report without raw batches. All 1,512 cells, 52 matched baselines,
and 141 families at three thresholds agreed with the retained evidence.

1. **Shell endpoint rounding.** A valid generated point
   `[.49999999999999994,0,0,.51,.019999999999999907]` at `h=.02` was classified
   as contact by the high-precision path, while subtraction from its rounded
   absolute arrival made the displayed free-horizon fraction exceed one.
   This contradicted the claimed implementation guarantee for the two
   confidence donors. Relative times now subtract before rounding, flagged
   free-event comparisons run at high precision before normalization, and
   authoritative joint counts retain their recheck metadata. The certain
   endpoint is evaluated as the analytic identity F(1,1)=1. Certified assurance
   uses exact analytic point enclosures for all known donor quantities;
   historical sampling CP intervals remain diagnostics.

   The generated boundary and analytic-endpoint regressions failed before the
   fix and pass afterward. All 20 original reference batches, totaling 20,000
   histories, were replayed with their original seeds. Every contact, censor,
   and joint integer count matched. The largest change in a displayed
   accepted mean was `6.661338147750939e-16`. The stellar intervals are
   unchanged. See `results/reference_endpoint_review.json` for hashes, seed
   identities, exact-control enclosures and the corrected assurance rule.

2. **Missing-store resume.** A published refinement with compressed completed
   checkpoints and look-5 state could start sampling batch zero when its raw
   store was absent. This could lose the cumulative batch boundaries. Resume
   and checkpoint-completion now reconcile saved hashes, compressed snapshots,
   execution records and completed-job records before simulation. State must
   retain preceding completed counts and cannot relabel advanced data as look
   one. New stores have durable paired inner/outer identities, so complete
   loss is detected even before the first aggregate snapshot. Missing storage
   produces an actionable restoration error; aggregate-only report generation
   remains supported. Regressions for refinement, unfinished original runs,
   checkpoint completion, missing state and complete store loss failed before
   the fix and pass afterward.

3. **Torn resource journal.** An incomplete last JSON append blocked usage and
   recovery, and a later start could append after the damage. Reads and appends
   now recover under the ledger lock, preserve interrupted bytes in hashed
   binary sidecars, retain the valid prefix, and reject corruption in completed
   records. A valid final JSON record missing only its terminator is preserved.
   Torn start/progress/finish, immediate append, prefix-corruption and
   published-batch recovery regressions failed before the fix and pass after it.

The post-review code intentionally has new execution hashes. Numerical
provenance remains pinned to `d21192c5428a1681fef1179530e8f06c53dde15b`;
frozen locks were not rewritten to pretend otherwise. Use that historical
checkout and its matching raw store to reconstruct the recorded numerical
run. Use the corrected current code for saved-evidence reports and newly
frozen experiments. The endpoint replay binds the correction to the retained
evidence without a broad stellar simulation rerun.

The focused recovery suite passed 50 tests, and the full suite passed 250
after the three fixes. Final readiness and reproduction records are under
`results/final_correctness.json`, `results/clean_reproduction.json`, and
`results/saved_evidence_reproduction.json`.
