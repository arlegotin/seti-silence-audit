# Continuous detector-efficiency refinement

Execution-method amendment, 2 November 2026. The original scientific grid,
compatibility thresholds, F1/F2 assumptions, and materiality rule are unchanged.

The original Dpositive calculation bounds each history over the whole interval
`p in [.44,.94]`, before forming bounds on the conditional risk. Its endpoints
need not be jointly attainable. In the first completed confirmation checkpoint,
this produced a risk upper bound near .40 for a high-activity slow-speed model.
It is a valid enclosure, not evidence that a .40 risk can actually occur.
Further sampling of that coarse enclosure is an inefficient remedy.

The replacement partitions the full efficiency interval into contiguous
subdomains. Within each subdomain it bounds null weights, their arrival and
nonarrival parts, and compatibility. It then takes the outer envelope over all
possibly compatible subdomains. It never assumes that risk is monotone in p,
and it never substitutes two endpoint risks for the continuous family.

The F1 response can be stored compactly: counts of possible/certain single
sources, and possible/certain visits to the one repeated source. Each single
source contributes `1-zeta*p*a`, where a is its activity bound. For the repeated
source the lower null factor uses the capped sum of visit-detection bounds and
the upper null factor uses their maximum. Compatibility is averaged once for
that physical source. Boundary eligibility is checked with the existing
arbitrary-precision comparator. This representation is tested against the
scalar and catalog batch likelihoods for every emission variant.

Fresh confirmation uses seed identities `[20261101,1,8,model,purpose,batch]`.
Original histories, sources, code identity, and completed checkpoints remain
available. The original engine finishes its already prescribed checkpoint
before handing the remaining nuisance/weak-detector precision work to this
method. That checkpoint is labeled `checkpoint_complete_refinement_pending`,
not a completed scientific conclusion. No partially completed look is promoted
into a fixed-sample confidence claim.

The original .05 total Monte Carlo error allowance is preserved. Twelve
diagnostic interval items concern ideal-silence S1 century-arrival risk. That
risk is identically zero: the catalog's nearest site is about 30.789 light-years
away, giving a minimum S1 silence-to-arrival gap of about 277.102 years. Their
all-zero exact-binomial intervals include zero at every checkpoint, so their
actual noncoverage probability is zero. From a diagnostic pool A=.025 with
M=2536, their allocated share `A_ref=.025*12/2536` can therefore fund the fresh
refinement without increasing the original error bound. This is a geometric
proof, not selection of intervals that happened to have favorable outcomes.

Divide A_ref among P unique refined parent quantities, checkpoint looks j,
and the N_j subdomains at that look:

`alpha = A_ref / [P*j*(j+1)*N_j]`.

Shared likelihood quantities across future continuations reuse the same
interval and counts. Initial refinement uses 100,000 survivors per setting and
16 efficiency subdomains; cumulative histories and subdivisions double as
needed. There is no maximum look. Fixed-efficiency Dweak comparisons use one
point subdomain. Independent-site subdomains use validated quadrature rather
than Monte Carlo. Existing error-free intervals are still displayed; their
proof explains why the reassignment does not double-spend error probability.

One cannot in general reclaim an unused tail of a fixed-look confidence
allocation after inspecting data. That approach was considered and rejected
before fresh refinement confirmation. The saved refinement lock records the
actual donor proof, interval identities, pool, code, upstream result hash,
seeds, and precision rule.

Original per-model rows retain the coarse calculation. Reports separately
export the refined subdomains, recompute the affected family envelopes, and
bind them to the saved refinement evidence. Missing empirical scan times and
final-selection calibration remain empirical limitations; a loose numerical
enclosure is not relabeled as such a limitation.
