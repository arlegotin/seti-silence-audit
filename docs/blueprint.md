# PoC execution brief: what does a real SETI null say about physical arrival?

**Executor:** an autonomous coding agent configured as `gpt-6.1-sol` with `xhigh` reasoning.  
**Research and source-audit date:** 1 November 2026.  
**Target machine:** one MacBook with an M3 Max; inspect its actual RAM, free storage, operating system, and Python environment before allocating work.  
**Deliverable you must produce:** a reproducible, scoped research result, including runnable code for the stages reached and an evidence-backed report. This document is the plan; it is not a report of a completed PoC.

## 1. Project decision, contribution, and scope

Implement **a finite-target audit of the inference from the UCLA 2020–2023 Green Bank Telescope radio null to physical arrival during the following 100 years**. Use the supplied continuum theorem as an independently checked mathematical reference. The computational mechanism is chronological birth suppression at fixed stellar sites, coupled to an explicit likelihood model of the survey's observing and selection procedures. Compare it with an exactly integrable independent-site control and with the much stronger perfect-silence observation.

The smallest defensible contribution is a reproducible answer to this question:

> **Within the declared finite population and detector families, does the UCLA null materially reduce the upper envelope of century-arrival probabilities relative to conditioning only on no previous arrival, and which emission, calibration, interaction, and continuation assumptions are responsible?**

Do not frame the project as forecasting extraterrestrial visitation. A result that the observation has no robust constraining power is useful. A finding that a calibrated final-selection likelihood cannot be recovered from the available data is also useful, provided you identify the missing information and complete the unaffected mathematical and computational audit.

### 1.1 What is new enough to investigate

Existing work already covers Poisson expansion, observability conditional on non-occupation, incomplete SETI detection, and null-survey updating of expanding-civilization models. In particular, Olson and Ord explicitly include a detection fraction in a cosmological null likelihood [R6, Section IV, Eqs. 14–20]. The UCLA paper already corrects transmitter-prevalence limits for pipeline efficiency and duty cycle [R2, Section V.2]. Reproducing those corrections is not this project's contribution.

Gams, Kosanović, and Stopar also provide a generic completeness/product-likelihood layer and a reduced MWA Vela null application [R14, Supplement Sections S5.5–S5.14]. Thus a survey likelihood, reweighting, or a real-survey example alone is already prior art.

The proposed addition is the **instrument-specific connection to interacting physical arrival events at the actual primary target sites**, with linked observations and explicit calibration uncertainty. Its value is demonstrated by showing where an ideal-silence substitution, an independent-site approximation, or an unjustified detector transfer changes the inference. Do not claim historical priority for the simulator, first-clock reduction, partial identification, or the theorem's exponent transition. The literature review found no directly equivalent audit, but was not exhaustive; a limited-overlap assessment is the strongest supported novelty statement.

### 1.2 Necessary revisions to the initial formulation

1. **Physical sites versus target rows.** Appendix A of the survey contains 62 rows but 61 distinct TOI identifiers. TOI 1730.01 occurs in both tables at the same coordinates and distance. Use one physical birthplace with repeated observing visits unless the observing records establish a table error. This preserves the intended primary-target restriction; it does not add field stars. Reconcile identities before freezing the catalog.
2. **Hit recovery versus final detection.** The reported injection matches do not independently determine success through both ON scans, directional rejection, and final adjudication. Treat the conversion to a final-selection probability as an explicit transfer assumption or uncertainty.
3. **Exact survey versus coarsened information.** Scan timestamps were not retrieved during planning. The exact endpoint `t0` remains a data gate. If normal access still fails, execute the coarsened-survey bounds specified below. Do not invent an observing schedule or report that fallback as an exact reconstruction.
4. **Finite experiment versus continuous parameter optimization.** The principal numerical claims concern a predeclared finite scenario family, supplemented by conservative bounds for specified continuous detector uncertainties. A grid envelope is not a bound over every rate, speed law, or emission history.

These revisions leave the practical purpose intact. They give up a universal Galactic prediction, a fully calibrated arbitrary-signal likelihood, and any claim that continuum asymptotics directly describe the catalog.

### 1.3 Primary comparison and decision threshold

For each declared family, report all three intervals:

- `I0`: the envelope of arrival probabilities conditioned only on no prior arrival, over the original family.
- `Iselect`: the same probabilities over models compatible with the radio null.
- `Ipost`: the probabilities additionally conditioned on the radio null, over compatible models.

This separates exclusion of models from updating within a retained model. Also report every per-model likelihood and risk.

Let `U0` and `Upost` be the upper endpoints of `I0` and `Ipost`. The prespecified **material narrowing** criterion is

\[
U_0-U_{\rm post}\ge 0.01,\qquad
\frac{U_0-U_{\rm post}}{U_0}\ge 0.25.
\]

Both inequalities must be certified after numerical and Monte Carlo uncertainty is included. If \(U_0=0\), the ratio is not defined and no narrowing is claimed. One percentage point and 25% are research-resolution conventions chosen before comparison, not societal risk tolerances or evidence about plausible alien probabilities. Report smaller effects numerically when resolved, without calling them material.

The primary conditional test is the **persistent, survey-admissible bright-emitter family** under the nominal detector-transfer assumption, with historical age 10,000 years and unchanged future birth rate. Test its robustness under the declared weaker detector, other emission histories, and future-rate alternatives. The all-civilization family including fully invisible counterparts has an analytic obstruction to envelope contraction (Section 4.3); do not spend a large simulation budget rediscovering it.

A positive result requires trustworthy numerical intervals and a precise statement of the assumptions supporting it. An adequately precise failure to meet the threshold is an informative negative for this finite family. Wide intervals, inaccessible calibration, or omitted unresolved parameter cells make the relevant claim inconclusive, not false.

## 2. Inputs, evidence status, and acquisition

### 2.1 Required and recoverable inputs

The original attachments were:

| Input | Original planning-workspace location | Status |
|---|---|---|
| `silence_contact_theorem.pdf` | `/workspace/scratch/367f0e3f319b/upload/silence_contact_theorem.pdf` | Read in full: 14 pages; critical equations visually inspected |
| `Pasted text(20261101-120455).txt` | `/workspace/scratch/367f0e3f319b/upload/Pasted text(20261101-120455).txt` | Full project request; its operative requirements are incorporated here |

Those paths identify provenance; they will not automatically exist on the Mac. Place the theorem, if supplied with the handoff, at `inputs/silence_contact_theorem.pdf`. Its SHA-256 is:

`2a6c071a3edfc6ff3dc5db07ac4c94448537f907e9e22051f9397b49374839fe`.

The instruction attachment has SHA-256:

`955cb73e1224205f1111bdbaeec90a2fce21d394dcf6e902093ea15207f31989`.

The essential mathematics and target table are reproduced or independently derived in this brief, so the executable study does not require undocumented code from the conversation. If the PDF is absent, you may implement the equations here, but cannot claim to have independently re-inspected its source. Request that one file only if source-level reinspection becomes necessary.

Use the versioned UCLA paper [R2], the candidate archive [R3], and the target transcription in Appendix B. Fetch small source documents first. Do not download telescope raw-voltage data or attempt to recreate the signal-processing pipeline.

Use the following evidence labels in metadata and the report:

- **Source theorem:** a mathematical result claimed and proved in the supplied note, under its stated assumptions.
- **Source observation:** a reported survey or injection result.
- **Planning derivation:** an equation or algorithm derived for this brief.
- **Planning probe:** a small computation actually performed while preparing the brief.
- **Model assumption:** an unmeasured population, detector-transfer, or continuation choice.
- **PoC finding:** a result produced by your implementation, with its validation and uncertainty.

### 2.2 Compact empirical facts that determine the detector design

The selected survey used four sessions: 2020-04-22, 2021-04-28, 2022-05-22, and 2023-05-13. Each target visit used two 150-second ON scans in ABAB source pairs. The selection rejects single-ON hits and zero-drift signals. Injections used 2021 data, linear chirps, approximately 20 recovered SNR, and sampled frequencies/drifts; recovered hits were matched within 6 Hz and 0.05 Hz/s. Counts were 9400/10000 overall and 6716/6807 outside dense RFI. The published band is 1.15–1.73 GHz, excluding a notch whose prose boundary is rounded; Figure 2 specifies 1.2000–1.3412 GHz. Drift coverage is approximately ±8.86 Hz/s. Appendix A supplies positions and distances [R2, Section II, III.4, III.7, IV.2/Table 2, Appendix A].

The inference audit is restricted to a received-signal class comparable to those injections. An intrinsic EIRP threshold alone does not guarantee that class, particularly under amplitude variation or propagation effects [R12, Section 2].

### 2.3 Archive contents and an explicit access gate

Dryad version **370211**, published 2025-06-13, contains four candidate-detection CSVs, totaling **4,353,609,517 bytes**, plus a 2,665-byte README. It is not an injection-truth dataset. Relevant fields include `NAME, SCAN, MJD, FREQ, DFDT, FSNR, FDOP, FBTH, FOTH, FAND, PARTNER` [R3].

During planning, the landing page and metadata API were readable; bounded file-download attempts returned HTTP 403 on the website route and 401 on the API route. No candidate CSV contents or exact scan times were obtained. This does not establish that downloading on the user's Mac will fail.

Attempt normal public or already-authorized access, using the dataset landing page and returned download links. Verified metadata routes are:

- `https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.wm37pvn0b`
- `https://datadryad.org/api/v2/versions/370211`
- `https://datadryad.org/api/v2/versions/370211/files`

Do not bypass authentication, scrape credentials, or contact authors autonomously. Allow at most two ordinary attempts per failed route within the acquisition time cap. Preserve status codes and metadata.

If downloads work, stream each CSV once, extracting only unique observing metadata and a small validation sample. Use a streaming CSV reader; never load four gigabytes into a dataframe. Hash the original bytes while streaming. Keep compressed/raw originals only if disk permits; preserve exact identifiers, hashes, and the reduced schedule in all cases.

Create:

```text
visits.csv:
visit_id,site_id,session_date,scan_index,start_mjd,duration_s,end_mjd,
paired_visit_id,source_file,provenance_status
```

A `visit_id` denotes one target's two ON scans in one ABAB block; `scan_index` identifies its member scans. Validate both scans for every visit, the ABAB chronology, the target names, repeated visits, session membership, and duration. A source's observation of the paired target serves as an OFF direction; it is not another independent draw of that source's civilization.

Set

\[
t_0=\max_j(\mathrm{start\_MJD}_j+150/86400)
\]

only after verifying that this is the complete selected schedule and that the 150-second duration applies to every scan. Candidate records with zero hits could be absent from the archive. A maximum timestamp without a completeness check is insufficient.

If a log is unavailable, the minimal useful additional input is a small authorized extract of unique `(source_file, NAME, SCAN, MJD)` tuples and durations, or the telescope's observing log. Continue all unaffected work without waiting for it.

### 2.4 Bounded fallback when timestamps or final calibration remain unavailable

**Fallback F1: coarsened-survey audit.** Use the exact published primary-target geometry, the two-year visit groups in Appendix B, and conservative observing-time intervals. The first group's scans lie on one of the first two session dates; the second group's lie on one of the last two. Do not assume a 16/16 split or assign individual years without evidence.

The final observation occurred in the final stated session. For a concrete conservative fallback, assume each approximately two-hour session began on its reported UTC date and allow all of its scan times within the 48-hour interval from that date's midnight through the end of the following date. Thus the endpoint interval is \([2023\text{-}05\text{-}13\ 00{:}00,\ 2023\text{-}05\text{-}15\ 00{:}00]\) UTC. Record this date interpretation as an assumption; correct it using verified metadata if available before protocol freeze.

In all computations, time zero means the actual, unknown final endpoint. Subtract the endpoint interval from each possible session interval, retain the union over a target's allowed dates, and intersect with times at or before zero. Use interval arithmetic: \([a,b]-[c,d]=[a-d,b-c]\). The demographic model is defined relative to this zero; no arbitrary noon or midnight becomes a substitute datum. This relaxation preserves all admissible schedules, although it also includes impossible combinations.

For each latent history, construct lower and upper null weights using the explicit per-visit and per-source algorithm in Section 6.5, then the inference bounds in Section 7.4. Preserve 150-second ON durations and two nonoverlapping ON integrations per visit; do not invent minute-scale gaps, individual observing years, or independence between repeated visits. Bounds may be wide and still identify the consequence of missing information.

This fallback can establish a conditional or partially identified result for a coarsened survey. It cannot claim an exact reconstruction of the original \(R_\theta\).

**Fallback F2: final-selection calibration absent.** Complete the detector-assumption sensitivity and the analytic unconstrained-detector result. Label numerical results with assumed final-selection efficiency as conditional. Do not promote them to a calibrated empirical bound. If no nontrivial evidence-backed detector lower bound exists, report that limitation explicitly.

Neither fallback authorizes replacing the target catalog with favorable synthetic stars. Synthetic cases remain correctness controls.

## 3. Mathematical reference: what the supplied theorem actually supports

### 3.1 Objects and assumptions

In the note [R1, pp. 2–3], potential births are a Poisson process on

\[
\mathbb R^d\times[0,\infty)\times(0,c)
\]

with intensity \(\lambda\,dx\,dt\,dF(q)\), where \(q=c/V-1>0\), \(d\) is a positive integer, \(c>0\), and \(\lambda\) has units length\(^{-d}\) time\(^{-1}\). The observation point is fixed in advance at the origin. A birth at \((x,t)\) has hypothetical times

\[
D=t+\|x\|/c,\qquad A=t+\|x\|/V.
\]

Accepted births emit immediately and persistently with perfect detection, expand forever as balls, and suppress later births inside earlier accepted balls. Overlap does not stop a front. There is no extinction, collision shielding, stellar motion, or anthropic sampling rule.

Let \(S_T\) be no accepted signal by \(T\), \(H\) the next physical-arrival delay, and \(Q\) the first accepted signal delay. If

\[
F(z)\sim Cz^\alpha,\qquad z\downarrow0,\quad C,\alpha>0,
\]

the theorem states, for fixed \(T,\lambda,F\), as \(h\downarrow0\),

\[
p_T(h)=\Pr(H\le h\mid S_T)\sim
\begin{cases}
\dfrac{\lambda\nu_dc^d C d}{(d-\alpha)(\alpha+1)}
 T^{d-\alpha}h^{\alpha+1},&\alpha<d,\\[5pt]
\dfrac{\lambda\nu_dc^d C d}{d+1}
 h^{d+1}\log(T/h),&\alpha=d,\\[5pt]
\dfrac{\lambda\nu_dc^d}{d+1}\mathbb E[q^{-d}]h^{d+1},
&\alpha>d,
\end{cases}
\]

where \(\nu_d\) is the unit-ball volume. Conditional on \(S_T,H\le h\),

\[
(Q/h,(H-Q)/h,1-H/h)
\Rightarrow \operatorname{Dirichlet}(1,\rho,1),
\qquad \rho=\min(\alpha,d).
\]

The limiting density of the first two fractions is
\(\rho(\rho+1)y^{\rho-1}\) on \(x>0,y>0,x+y<1\). Equivalently, \(H/h\) and \((H-Q)/H\) tend to independent \(\operatorname{Beta}(\rho+1,1)\) and \(\operatorname{Beta}(\rho,1)\). These are small-horizon conditional laws, not century-arrival forecasts [R1, Theorem 1, E1–E4].

### 3.2 Why the suppression transfer works, and why the real survey breaks it

If accepted birth \(i\) suppresses candidate \(j\),

\[
\|x_i-x_j\|\le V_i(t_j-t_i),
\]

so the triangle inequality and \(V_i<c\) imply \(D_i\le D_j\). Every potential signal by \(T\) therefore entails an accepted signal by \(T\). Silence is exactly the empty past light cone, with

\[
\Pr(S_T)=\exp\left[-\frac{\lambda\nu_dc^dT^{d+1}}{d+1}\right],
\]

independent of the speed law [R1, Lemma 2/E5, p. 4]. The causal ancestry lies in a finite backward light cone, making the accepted process constructively well-defined.

Define

\[
B_h=\{T<D,\ A\le T+h\},\qquad C_h=\{T<D\le T+h\},
\]
\[
b=\mu(B_h),\qquad
s=\frac{\lambda\nu_dc^d}{d+1}[(T+h)^{d+1}-T^{d+1}].
\]

Every relevant suppressor lies in \(C_h\) under silence. The event of exactly one shell point, which belongs to \(B_h\), and a Poisson factorial-moment argument give

\[
b e^{-s}\le p_T(h)\le1-e^{-b},\qquad
0\le (1-e^{-b})-p_T(h)\le bs.
\]

The conditional marked-law discrepancy is bounded, for example, by \(2se^s=O(h)\) [R1, Lemma 3, pp. 4–5]. This transfers the leading asymptotics; it does not identify the finite-horizon accepted probability with the free-process exponential.

An invisible, expired, unobserved, or missed suppressor need not have been detected by the real survey. Consequently, the real null does not empty that light cone. Do not condition the empirical simulation on the theorem's silence event, and do not replace dependent suppression with independent Poisson thinning. Independent marking/thinning identities require their own assumptions [R9, Theorems 3.9, 5.6, 5.8 and Corollary 5.9].

### 3.3 Exact finite-age kernel and an explicit repair to the source

For the free continuum process [R1, E10, pp. 7–8],

\[
b(h)=\frac{\lambda\nu_dc^d}{d+1}\int K_T(q,h)\,dF(q),
\]
\[
K_T(q,h)=
\begin{cases}
h^{d+1}/q^d,&q\ge h/T,\\
(T+h)^{d+1}/(1+q)^d-T^{d+1},&0<q<h/T.
\end{cases}
\]

The two branches agree. The second branch is essential: extending the first branch to all \(q\) incorrectly introduces an infinite negative moment when \(\alpha\le d\).

For numerical stability, evaluate the low-\(q\) branch as

\[
T^{d+1}\operatorname{expm1}
\big((d+1)\operatorname{log1p}(h/T)-d\operatorname{log1p}(q)\big).
\]

Split quadrature at \(q=h/T\). Normalize by a known leading power before integration when values are tiny; a fixed absolute quadrature tolerance on an \(h^4\)-scale integral is inadequate.

**The formula defining \(L(h,u)\) on PDF page 8 is visibly incomplete in the PDF itself.** The following is an independent reconstruction from E8, not a quotation of missing source text. With \(a=uh/[T+(1-u)h]\),

\[
L(h,u)=\lambda\nu_dc^d
\left[
(T+h)^d\int_{(0,a]}(1+q)^{-d}\,dF(q)
+(uh)^d\int_{(a,\infty)}q^{-d}\,dF(q)
\right],
\quad L(h,0)=0.
\]

One derivation integrates
\(\lambda d\nu_dc^d w^{d-1}J(w/(T+h-w))\) from \(w=0\) to \(uh\), where \(J(a)=\int_{[a,\infty)}q^{-d}dF(q)\). Then

\[
b'(h)=L(h,1),\quad
\Pr(W_*/H_0\le u\mid H_0=h,S_T)=L(h,u)/L(h,1).
\]

\(W_*\) is the warning of the contacting free source, not necessarily the interval after the first signal from any source. Keep the complementary integration endpoints when testing atomic speed laws.

For a finite horizon \(h\), the corresponding exact free-process comparison is, for \(0\le z,u\le1\),

\[
\Pr(H_0\le zh,\ W_*/H_0\le u\mid H_0\le h,S_T)
=\frac{\int_0^{zh}e^{-b(x)}L(x,u)\,dx}{1-e^{-b(h)}}.
\]

In particular,
\(\Pr(H_0/h\le z\mid H_0\le h,S_T)=(1-e^{-b(zh)})/(1-e^{-b(h)})\).
Use these finite-horizon formulas for the shell experiment. Substituting \(L(h,u)/L(h,1)\) for the warning distribution conditional on \(H_0\le h\) would confuse conditioning on an exact arrival time with conditioning on an interval.

### 3.4 Audit findings and work already performed

A complete read of the supplied note and an independent mathematical review found no fatal defect in the main theorem or its suppression coupling. This is an audit judgment, not a formal verification. Its varying-rate extension [R1, E11, pp. 10–11] also appears consistent under bounded continuous rate and positive present rate; it is not needed for the empirical engine.

Small SciPy/binary64 checks performed during planning, on the hosted environment rather than the Mac, found:

| Check actually performed | Result |
|---|---|
| Kernel against direct radial integration, \(h=.1,\ q=.01,.1,1\) | Maximum absolute difference \(1.11\times10^{-16}\) |
| Printed \(\alpha=1,2\) closed forms at \(h=.001,.1,.5\) | Maximum relative difference \(3.34\times10^{-16}\) |
| Six tail examples at \(h=10^{-8}\) | Ratios reproduced to binary64 precision |
| Critical \(\alpha=3\) example | Exact/leading ratio about 1.03166730608; sampled warning-CDF error about .004620 |
| Five-point derivative \(b'(h)=L(h,1)\) | Maximum relative difference \(1.60\times10^{-13}\) |

The initial arbitrary-precision attempt could not run because `mpmath` was absent. The PDF's claimed 100-digit checks, its \(10^{-25}\)-scale errors, and its birth-suppression simulation were not independently reproduced. The referenced scripts `verify_contact_asymptotics.py` and `simulate_suppressed_contacts.py` and their result files were not attached. Reimplement only the bounded reference checks required below; do not claim possession of those scripts.

## 4. The actual inference problem and exact limitations

### 4.1 Definitions

Use light-years and Julian years, \(c=1\), and shift the actual final observation to time zero. Let \(h_*=100\). For a complete demographic history \(X\), containing accepted birth times, locations, and speeds, let

\[
A(X)=\min_{i\ {\rm accepted}}(b_i+r_i/v_i),
\quad A=\infty\text{ if no source can arrive},
\]
\[
E=\{A>0\},\qquad B=\{0<A\le h_*\}.
\]

Radio emission is attached to each accepted civilization's original stellar site. Colonized sites do not create additional transmitters or new birth sources in this model. State this modeling boundary; neither radio production at expansion fronts nor multigeneration colonization is calibrated here.

Define the history-conditional null weight

\[
w_\theta(X)=\Pr_\theta(N_{\rm det}=0\mid X),
\]

integrating over the specified emission and detector randomness while retaining same-source dependencies. \(N_{\rm det}\) counts extraterrestrial signals surviving the declared full selection operator. Ordinary RFI candidates rejected by that operator are not extraterrestrial detections.

The required quantities are

\[
C_\theta=\Pr_\theta(E),\qquad
\ell_\theta=\mathbb E_\theta[w_\theta\mid E],
\]
\[
R_\theta^0=\Pr_\theta(B\mid E),\qquad
R_\theta=\frac{\mathbb E_\theta[1_Bw_\theta\mid E]}
{\mathbb E_\theta[w_\theta\mid E]}.
\]

Equivalently, estimate the joint expectations
\(C=\mathbb E[1_E]\), \(G=\mathbb E[1_Ew]\), \(J=\mathbb E[1_Bw]\);
then \(\ell=G/C,\ R=J/G\). These identities are planning derivations from conditional probability.

Retain a fully specified model when \(\ell_\theta\ge\tau\), with \(\tau=.05\) primary and \(.01,.10\) sensitivity. This is a compatibility convention. It is neither a posterior probability for the model nor a 95% confidence bound on arrival.

The condition \(A>0\) is stipulated. It is not established by the telescope. Do not add an anthropic prior or penalize a model for small \(C_\theta\) unless explicitly reporting a different, exploratory question. Report \(C_\theta\) because it exposes that conditioning and determines computational difficulty.

### 4.2 A null can increase arrival probability

Exactly,

\[
R_\theta-R_\theta^0=
\frac{\operatorname{Cov}_\theta(1_B,w_\theta\mid E)}
{\mathbb E_\theta[w_\theta\mid E]}.
\]

Thus a null can reduce, leave unchanged, or increase the conditional risk. It depends on whether imminent-arrival histories tend to be detectable. Do not constrain plots, optimizers, or checks to \(R\le R^0\).

A synthetic exact control uses one birth at distance 100 ly and time \(-150\) yr. With probability \(1/2\), \(v=.5\) and it is radio-dark; otherwise \(v=.1\) and it is persistently bright. The arrivals are \(50\) and \(850\) yr. A detector with probability .94 on the bright branch gives
\(R^0=.5,\ \ell=.53,\ R=.5/.53\approx .9433962264\).
This tests the inference code and a joint speed/emission mark. It is not a fitted astrophysical scenario.

### 4.3 Analytic obstruction for all civilizations

For every demographic model \(d\), suppose the permitted family contains an otherwise identical emission setting that is completely invisible to this survey. This may mean no radio emission, emission outside its band, or no beam reaching Earth. Then \(w\equiv1,\ \ell=1,\ R=R^0_d\) for that setting.

Therefore,

\[
\{R^0_d:d\in\mathcal D\}
\subseteq
\{R_\theta:\theta\text{ retained in the full family}\}.
\]

The post-survey outer envelope cannot be narrower than the pre-survey demographic envelope. It may be wider: conditioning luminous models can yield additional probabilities outside the original envelope. This is not a proof that the range is \([0,1]\); its endpoints still depend on the population family.

An unconstrained final-verification factor allowing zero efficiency creates the same obstruction, even in a nominally radio-emitting family. Separate this data/calibration limitation from a conclusion that radio-bright expanders are unconstrained under every explicitly positive detector assumption.

### 4.4 Discrete sites and future behavior

For fixed sites with \(r_{\min}>0\), perfect silence and a strict cutoff \(v\le v_{\max}<1\) imply

\[
A\ge r_{\min}(1/v_{\max}-1)>0.
\]

The theorem's continuum power law cannot hold inside this exact gap. Under a near-light-speed tail, fixed sites within the finite-age light cone instead give a free-wedge leading order

\[
b_{\rm discrete}(h)\sim
\frac{C h^{\alpha+1}}{\alpha+1}
\sum_i \lambda_i r_i^{-\alpha}.
\]

There is no saturation of the exponent at four simply because coordinates have three components. These boundaries are already described in [R1, pp. 11–12]; they are controls, not a new discovery of the PoC.

The catalog transcription gives \(r_{\min}\approx30.7891621\) ly and \(r_{\max}\approx2752.955522\) ly. A birth after zero can arrive within 100 years only from a site with \(r<100v\). No such future birth contributes when \(v_{\max}\le .3\). Six listed sites lie within 100 ly (Appendix B). Earlier births can still arrive in the benchmark window.

Post-survey birth-rate multipliers and emission changes are continuation assumptions. A past null does not measure them. Future emission changes cannot alter the past-data likelihood; future births may alter physical arrival and must still obey birth suppression.


## 5. Freeze the scientific model before looking at survey-arrival comparisons

The following are **assumptions for a bounded diagnostic**, not inferred parameter distributions. Use equal hazard at each distinct primary site; do not fit a spatial prior or infer Galactic prevalence from this selected sample.

### 5.1 Demography, speed, and continuation

| Component | Fixed specification | Reason and limit |
|---|---|---|
| Geometry | Heliocentric 3D Cartesian coordinates from Appendix B; fixed stars and observer | Preserves distances and pairwise suppression; neglects proper motion and gravitational trajectories |
| Historical start | \(-B\), \(B=10{,}000\) Julian years; no preexisting expansion | Finite boundary is part of the model, not an estimate of civilization history |
| Historical rate | \(\lambda_i=\mu/(nB)\), \(\mu\in\{0.1,1,3,12\}\) | \(\mu\) is expected attempted births across all sites before zero; actual accepted count differs |
| Expansion | Constant-speed balls; permanent occupation; no stopping at overlap | Matches the suppression semantics of the reference |
| Speed S1 | \(v=.1\) for every birth | Strict subluminal cutoff |
| Speed S2 | \(v=.5\) for every birth | Faster cutoff; also permits some post-survey arrivals |
| Speed S3 | Probability .999: \(v=.1\); probability .001: \(q=U,\ v=1/(1+q)\), \(U\sim U(0,1)\) | A very small near-light-speed component |
| Speed S4 | \(q=U,\ v=1/(1+q)\) | An intentionally strong near-light-speed tail, not a favored physical prior |
| Future birth rate | \(k\lambda_i\) on \((0,100]\); \(k=1\) primary, \(k=0,10\) mandatory continuation controls | Past likelihood is identical across these continuations |
| Marks | Independent across attempted sites and from birth clocks in primary models | Joint speed/emission dependence appears only in the exact adversarial control |
| Other sources | None outside the resolved primary-target list | No Galaxy-wide conclusion |

There are **16 primary demographic ensembles** (four rates × four speed laws). Future continuations reuse their pre-zero histories but must replay subsequent acceptance with the altered future clocks. Emission and detector variants reuse exactly the same accepted demographic histories.

The \(\mu=12\) row must remain. During review, a cheap bound showed that the initially considered \(\mu\le6\) grid would force every primary model to be retained even at \(\tau=.10\): on these sites, \(\ell\ge P(S)/C_{.1}\approx .1403\) at \(\mu=6\), where \(S\) is ideal silence and \(C_{.1}\) is common-speed survival at .1. At \(\mu=12\) this lower bound becomes about .01969, so exclusion at .05 is no longer analytically prevented. The grid was changed for informativeness before any survey-arrival comparison, not to seek a favorable result. The exact proposal in Section 6.4 makes the higher rate computationally practical. Actual exclusion is still an experimental question.

For finite-age sensitivity, add **four declared diagnostic ensembles**: \(B\in\{1{,}000,100{,}000\}\), \(\mu=3\), speeds S1 and S4, \(k=1\). Here \(\mu\), not \(\lambda_i\), is held fixed, so these compare different historical allocations of a fixed expected attempt count. Label that choice; it does not isolate age while holding present rate unchanged. Do not claim robustness over all intermediate ages. The 100,000-year case is a mathematical stress of the fixed-position assumption, not a validated stellar-dynamics model.

A zero-rate model \(\mu=0\) is an analytic control, with \(R^0=R=0,\ell=1\), and requires no ensemble.

### 5.2 Emission families

Each accepted civilization emits only from its original star. Define the **survey-admissible signal class** as a narrowband, scan-local linear chirp with received amplitude comparable to the published SNR approximately 20 injections, within the searched drift range, and outside categories the declared procedure rejects automatically. Its received frequency track must remain within the adopted admissible frequency set during every relevant ON integration.

In MHz, adopt

\[
\mathcal F=[1150,1730]\setminus\big([1200,1341.2]\cup\mathcal M\big),
\]
\[
\begin{aligned}
\mathcal M={}&[1155.99,1196.91]\cup[1192.02,1212.48]\\
&{}\cup[1422.320,1429.992]\cup[1525,1559]\\
&{}\cup[1554.96,1595.88]\cup[1592.9525,1610.485].
\end{aligned}
\]

The inherited dense-RFI intervals are from [R11, Table 2]; the notch boundary is from [R2, Figure 2]. Their use as a common 2020–2023 admissibility mask is an explicit transfer assumption. They do not establish every session's additional rejection regions or the exact clean subset used in the injection experiment. Zero-drift signals and source populations causing cross-direction false association are also outside this class.

Let \(\zeta\) be the probability that a civilization belongs to this class and directs its emission toward Earth. Draw that status once per source, independently of the primary demographic marks. Its complement has zero detection probability while expansion remains unchanged. The primary bright family conditions on admissibility, so its frequency gate equals one: **do not multiply its likelihood by an additional full-band coverage fraction**.

If explicit frequency marks are introduced in a diagnostic, apply the mask to the same source-level status and retain the mark across scans and visits. A masked or out-of-band signal has zero detection probability under the declared operator, including Duncal. Do not redraw frequency admissibility or count it twice through both \(\zeta\) and a coverage multiplier. The primary simulator need not generate raw signals or add a full-band frequency-population model.

| ID | \(\zeta\) | Delay after birth | Emission duration | Temporal activity while alive |
|---|---:|---:|---:|---|
| E1, primary bright | 1 | 0 | Infinite | Always ON |
| E2, sparse compatible | .1 | 0 | Infinite | Always ON |
| E3, delayed | 1 | 100 yr | Infinite | Always ON |
| E4, short-lived radio | 1 | 0 | 100 yr | Always ON |
| E5, intermittent | 1 | 0 | Infinite | Stationary two-state process below |
| E0, fully invisible | 0 | Any | Any | Analytic \(w=1\) |

Radio cessation does not stop physical expansion. Frequency mismatch, an Earth-missing beam, and radio silence are separate physical interpretations of the zero-detectability class; these data cannot distinguish them. Do not infer their relative frequencies.

For E5, use a stationary continuous-time Markov chain with ON fraction \(f=.1\), correlation time \(\tau_c=1\) day, OFF-to-ON rate \(a=f/\tau_c\), and ON-to-OFF rate \(b=(1-f)/\tau_c\). Initialize the process in its stationary state at emission onset. Evolution between observing windows uses exact transition probabilities, not a daily or minute grid:

\[
P_{11}(\Delta)=f+(1-f)e^{-\Delta/\tau_c}.
\]

Requiring the signal to remain ON through an integration window of duration \(d\) contributes \(e^{-bd}\) when initially ON. Do not replace two ON requirements by a single duty-cycle multiplier or by two independent source draws.

The primary detector-transfer abstraction requires a comparable narrowband signal throughout each complete ON integration. Partially illuminated scans are outside that transfer class. Setting their detection to zero defines the point scenarios and Dpositive; it is not a claim that the actual pipeline can never recover them, nor a guarantee that the resulting arrival risk is conservative. Duncal also allows uncertain recovery from partial integrations using the broader temporal bounds in Section 6.5.

### 5.3 Detector scenarios and uncertainty sets

For an admissible source satisfying the full-ON eligibility rule, use final-pair recovery probability \(p_{\rm pair}\). Set the **assumed per-ON recovery parameter** \(\eta_*=.94\). It is deliberately lower than the reported clean-subset hit recovery \(6716/6807\approx .98663\), but is not a measured efficiency of the adopted class, an empirical lower confidence bound, or a guarantee of conservative arrival inference. The principal numerical scenarios are:

| Detector ID | \(p_{\rm pair}\) | Interpretation |
|---|---:|---|
| Dnom | \(.94^2=.8836\) | Independent per-ON hit misses with assumed marginals \(\eta_*\); perfect survival of remaining stages after the fixed gate |
| Dweak | \(.5(2(.94)-1)=.44\) | Lower Fréchet pair probability for assumed marginals \(\eta_*\), followed by an assumed .5 remaining-survival factor |
| Dhigh | .94 | Maximally correlated per-ON recovery for assumed marginals \(\eta_*\), with perfect remaining survival |
| Duncal | No positive lower bound; probabilities in \([0,1]\) | Unknown final response on admissible signals, including possible partial-scan response; deterministic blind regions remain blind |
| Dpositive | \([.44,.94]\) | Continuous full-ON assumption envelope covered by history-weight bounds, not just endpoint risk estimates |

Dnom, Dweak, Dhigh, and Dpositive are **assumption scenarios**. Neither .44 nor .94 is a measured lower/upper confidence bound on final verification. The known admissibility gate acts before these recovery scenarios. Perfect remaining survival never overrides a deterministic frequency rejection. Duncal reflects the absence of a justified calibration bridge; the admissible zero-response member has \(w=1\), so the analytic noncontraction result applies. A complete sharp Duncal risk envelope is not required: report that obstruction and any valid outer bounds, without claiming its achievable range is necessarily \([0,1]\).

The Fréchet bound for both ON hits with equal marginal \(\eta\) is
\(\max(0,2\eta-1)\le p_{\rm both}\le\eta\).
The OR expression \(1-(1-\eta)^2\) implements the wrong rule.

The published \(9400/10000=.94\) describes hit recovery over the broader usable-frequency injection population. The \(6716/6807\) result describes its clean subset. Preserve both original denominators; neither independently measures the full two-ON, directional, and adjudication procedure. Frequency-subset differences, other observing years, interference dependence, and remaining verification are transfer uncertainties.

A planning calculation gives a 95% Clopper–Pearson interval of approximately [.935166,.944576] for 9400/10000 **if those injections can be treated as IID Bernoulli calibration trials**. This is descriptive sampling uncertainty for that broader population, not an uncertainty interval for \(\eta_*\) in the adopted class. It does not cover the transfer uncertainties above. Store the assumed parameter separately from the two empirical numerator/denominator records. No additional clean-subset parameter sweep is required.

### 5.4 Dependence assumptions that make the likelihood well-defined

Conditional on demographic history and fixed detector parameters, assume different accepted sources have independent compatible-emitter statuses and independent emission chains. Nominal recovery failures are independent between distinct visits after conditioning on their activity. Within each visit the pair probability already encodes its two-scan dependence.

This is an abstract selection model. It assumes no consequential overlap of extraterrestrial tracks with one another, no cross-target false association, and no unmodeled shared detector failure. The actual directional procedure can reject matches across sky directions, so identical or coordinated beacons are outside that factorized model. Do not count them as independently calibrated detections.

For repeated visits to a source, also report a dependence-robust null-weight interval. If their marginal detection probabilities are \(d_j\), the probability of at least one detection lies between
\(\max_j d_j\) and \(\min(1,\sum_j d_j)\). This bound requires no independent-visit assumption. For a source with uncertain common compatibility status, form the bounds conditional on that status, then average once over \(\zeta\).

Treat a shared calibration parameter as shared: evaluate each fixed nuisance setting or valid bounds over it. Integrating a separate efficiency for each source would be a different model.

## 6. Implementation specification

### 6.1 Units, inputs, and numerical conventions

Use binary64 CPU arithmetic for the demographic engine. Convert parsecs to light-years with

\[
1\,{\rm pc}=\frac{648000}{\pi}\,
\frac{149597870700}{299792458\cdot365.25\cdot86400}\ {\rm ly}.
\]

Use the published distances as fixed nominal inputs, not exact physical truths. Parse negative-zero declinations correctly. For right ascension \(\alpha\) in radians and declination \(\delta\),

\[
x_i=r_i(\cos\delta\cos\alpha,\cos\delta\sin\alpha,\sin\delta).
\]

Precompute the \(n\times n\) Euclidean distance matrix \(d_{ij}\), with zero diagonal, and Earth distances \(r_i\). Retain the input angular coordinates and source-row identifiers for audit. Never use angular distance alone for expansion.

A MJD is a time stamp, not a Julian year. Convert relative day differences to years by division by 365.25, and seconds by \(365.25\cdot86400\). Record time-scale assumptions; do not repeatedly round to calendar dates. The timing precision of the archive is not evidence of equal astrophysical precision.

Use \(A=\infty\) as a computational marker for no arrival within the tracked candidate history, with a separate right-censoring flag at \(h_*=100\). It does not assert that contact never occurs after the simulated horizon. Use finite candidate lists through 100. Candidates born after 100 cannot affect earlier arrivals or suppression and can be omitted. Accepted births at earlier times may have \(A>100\); retain their expansion for suppression even if they cannot themselves arrive during the benchmark.

Implement source-time emission windows and observation windows in one coordinate system. A scan at observer time \(o\) samples source time \(o-r_i\). For an accepted birth \(b_i\), delay \(\delta_i\), and lifetime \(L_i\), the received emission interval is
\([b_i+\delta_i+r_i,\ b_i+\delta_i+L_i+r_i)\).

Use exact inequality conventions: a birthplace is occupied at its front-arrival time; accept only when \(b_i<O_i\). No prior arrival means \(A>0\); the benchmark includes \(A=100\). Continuous random clocks make ties probability zero, but deterministic controls must respect these conventions.

Define a flagging tolerance \(\max(10^{-12}\ {\rm yr},64\epsilon_{\rm mach}\max(1\ {\rm yr},|\text{relevant times}|))\). Use it only to flag ambiguous comparisons, never to move event boundaries. Log flagged comparisons. Recheck them with extended or arbitrary precision rather than silently changing outcomes. Store \(q\) as well as \(v\); avoid an accidental atom at \(v=1\) from endpoint uniforms or rounding. If `nextafter(1,0)` is needed, count its use and bound its affected probability mass.

### 6.2 Exact first-attempt reduction

For permanent occupation at fixed sites, only each site's first potential attempt can matter:

- If accepted, its own site becomes permanently occupied.
- If rejected, the site was already permanently occupied.
- Every later attempt at that same site is therefore rejected.

This planning derivation reduces the exact finite accepted process to at most \(n\) candidate events. It does not assume a low birth rate, and it does not apply to extinction, vacant-site rebirth, or collision-limited fronts.

For cumulative hazard

\[
\Lambda_i(t)=
\begin{cases}
0,&t<-B,\\
\lambda_i(t+B),&-B\le t\le0,\\
\lambda_i B+k\lambda_i t,&0<t\le100,
\end{cases}
\]

draw independent \(e_i=-\log U_i\), \(U_i\in(0,1)\), and set
\(b_i=\inf\{t:\Lambda_i(t)\ge e_i\}\). If \(e_i>\Lambda_i(100)\), use \(b_i=\infty\). Draw one speed mark for that candidate. Marks of candidates eventually rejected cannot generate emissions or suppression.

### 6.3 Chronological accepted-process algorithm

Implement a straightforward scalar reference first. Its output includes accepted IDs, their birth times/speeds, earliest arrival, occupation times, and enough diagnostics to replay a history.

```text
simulate(first_clocks b[1:n], speeds v[1:n], coordinates, intersite=True):
    order = finite candidates with b <= 100, sorted by (birth_time, site_id)
    occupation[1:n] = +infinity
    accepted = []
    earth_arrival = +infinity
    for i in order:
        if intersite and b[i] >= occupation[i]:
            record suppressed i and its earliest accepted suppressor
            continue
        accept i
        accepted.append(i)
        earth_arrival = min(earth_arrival, b[i] + r[i]/v[i])
        if intersite:
            for j in 1:n:
                occupation[j] = min(occupation[j], b[i] + d[i,j]/v[i])
        else:
            occupation[i] = b[i]
    return accepted, earth_arrival, occupation, diagnostics
```

Every occupied ball continues to grow through overlap. A suppressed source never suppresses anything else. Do not remove a slow accepted ball when a faster ball overtakes it.

Cost is \(O(n^2)\) per history and \(O(n^2)\) fixed geometry memory. A batch of 4096 histories × 61 binary64 clocks is about 2 MB for that array; several simultaneous arrays still require explicit memory measurement. Avoid a full `batch × n × n` tensor when a rank-wise update suffices.

Batch the validated algorithm with NumPy if needed. No GPU, CUDA, neural model, or spatial grid is necessary. A compiled accelerator is not part of the required stack. Add one only if a measured bottleneck blocks a prespecified gate, within the repair allowance, and verify pathwise equality against the scalar engine.

### 6.4 Exact survival proposal for fixed and mixed speeds

Let \(v_*\) be a known lower bound on every speed in the chosen law. Use \(v_*=.1\) for S1 and S3, and \(v_*=.5\) for S2 and S4. Define

\[
E_*=\{\text{no potential attempt has }b_i+r_i/v_*\le0\},\qquad
C_*=\exp[-\sum_i\lambda_i(B-r_i/v_*)_+].
\]

**Planning derivation, independently checked:** actual accepted survival satisfies \(E\subseteq E_*\). If an attempted birth \(j\) violates \(E_*\) and is accepted, its actual arrival is at most \(b_j+r_j/v_*\le0\). If it is suppressed by accepted \(i\), then

\[
A_i=b_i+r_i/v_i
\le b_i+d_{ij}/v_i+r_j/v_i
\le b_j+r_j/v_*\le0.
\]

Thus restricting the *lower-support-speed* potential cone loses no surviving accepted history. This is not the invalid restriction that each candidate's own marked hypothetical arrival must exceed zero.

Sample independent clocks conditional on \(E_*\) by placing each clock origin at \(l_i=\max(-B,-r_i/v_*)\). With \(e_i\sim\operatorname{Exp}(1)\), set

\[
b_i=\Lambda_i^{-1}\!\left(\Lambda_i(l_i)+e_i\right),
\]

using \(b_i=\infty\) if the argument exceeds \(\Lambda_i(100)\). The hazard offset must not be omitted. Draw actual speed marks from their original law, run chronological suppression, and reject only histories whose **accepted** arrival is at or before zero. Accepted proposals are independent draws from the exact \(E\)-conditioned law.

For S1/S2, all speeds equal \(v_*\); \(E=E_*\), so no proposal rejection is needed and \(C=C_*\) exactly. For S3/S4, denote proposal acceptance by \(a=\Pr(E\mid E_*)\). Then \(C=C_*a\). Estimate \(a\) in a **separate fixed batch of 50,000 proposals per mixed-speed demographic setting**, with an exact binomial interval; multiply its endpoints by \(C_*\). Charge this diagnostic to the same compute/history caps. Do not substitute the ratio from a survivor-stopped run without a separately justified inverse-sampling interval. Use the \(C\) interval when forming \(P(S)/C\) in Section 6.7.

Validate the subset and resulting conditional distribution by finite enumeration and by ordinary unconditional rejection at inexpensive low-rate settings. An independent planning enumeration of 1,728 three-site finite-support histories found 294 actual surviving histories, all among 486 \(E_*\) histories; direct and proposed conditional risks agreed exactly. This is a tiny diagnostic, not a survey simulation.

Ideal silence obeys \(S\subseteq E\subseteq E_*\), yielding the useful acceptance bound \(a\ge P(S)/C_*\). With \(B=10{,}000,\mu=12\) and the transcribed geometry, \(P(S)\approx1.05713\times10^{-5}\). The bound is approximately .0196873 for \(v_*=.1\), and .581214 for \(v_*=.5\). The latter applies to S4. The sparse fast component in S3 may make its actual acceptance much higher than its conservative bound, but measure that before allocating work.

These are analytic/planning calculations, not M3 timing measurements. Keep the mixed-speed attempt cap and the unresolved-cell rules. No importance-sampling rescue is authorized in this first PoC: the exact unweighted proposal already avoids the principal rare-survival waste.

**Future replay.** Preserve each surviving history's pre-zero candidates, accepted sources, marks, and occupation fronts. Only sites with no first attempt by zero receive a residual \(e_i^+\sim\operatorname{Exp}(1)\), independent of the past. Their future first attempt is at \(e_i^+/(k\lambda_i)\), or infinity for \(k=0\); censor attempts beyond 100. Use the same residual hazard and speed mark across \(k=0,1,10\) for pairing, and replay chronological suppression with the unchanged pre-zero fronts. A site whose first pre-zero attempt was rejected remains permanently irrelevant. Future rate changes do not change \(E\), \(C\), or the past survey likelihood. Charge every replay's work to the cumulative ledger and history-evaluation cap.

### 6.5 Linked observation likelihood

For source \(i\), let \(\mathcal V_i\) be all its visits. Given that it is in the compatible class, let \(G_i(S)\) be the probability that the full ON windows of every visit in a nonempty subset \(S\subseteq\mathcal V_i\) are temporally eligible.

For persistent, delayed, and finite-duration cases, \(G_i(S)\) is a deterministic 0/1 containment test. For E5, if all selected windows lie after emission onset, sort and merge any overlapping windows and compute

\[
G_i(S)=
 f\exp\left[-b\sum_{m} d_m\right]
 \prod_m P_{11}(\mathrm{gap}_m).
\]

If any selected window lies outside the finite emission interval, set \(G_i(S)=0\). This formula integrates over a single source's emission history, including its correlation across separated visits; it does not simulate millions of unobserved daily state changes.

Under the specified independent recovery-between-visits assumption,

\[
w_i
=1-\zeta
\sum_{\emptyset\ne S\subseteq\mathcal V_i}
(-1)^{|S|+1}
G_i(S)\prod_{j\in S}p_{{\rm pair},j}.
\]

The published list implies at most two visits per physical site; confirm that against the logs. Inclusion–exclusion is cheap at this size. For one visit this is \(1-\zeta p_{\rm pair}G_i\). For two it is
\(1-\zeta[p_1G_1+p_2G_2-p_1p_2G_{12}]\).
A product with a separate \(\zeta\) draw for every visit is wrong.

Under the cross-source independence assumptions,

\[
w(X)=\prod_{i\ {\rm accepted}}w_i.
\]

Rejected candidates contribute no emission. No accepted source gives \(w=1\). Use log probabilities and `log1p`, with explicit handling of zero weights. Evaluate all emission/detector variants on the same demographic histories. Check every computed weight lies in [0,1] within numerical tolerance; a substantive violation is an implementation failure.

For timing or detector intervals, calculate conservative \(w^-(X)\le w_\theta(X)\le w^+(X)\). With exact times and the specified dependence model, increasing pair success at fixed history cannot increase its null probability, so Dpositive can be bounded by evaluating the weight at its two endpoints. This monotonicity of **weights** does not imply monotonicity of the posterior risk.

**Executable F1 construction.** For a visit \(j\), form the union \(O_j\) of possible relative observing-time intervals from Section 2.4. Keep distinct session alternatives as separate interval components; merge overlaps. Let \(I_i=[b_i+\delta_i+r_i,b_i+\delta_i+L_i+r_i)\) be the source's received emission interval and \(d=150/(365.25\cdot86400)\) years. Apply these inexpensive safe tests:

1. Full-window coverage is **certain** if \(I_i\) contains all of \(O_j\).
2. Full-window coverage is **impossible** if every component \(O\) of \(O_j\) has \(\operatorname{length}(I_i\cap O)<2d\). Two nonoverlapping full ON integrations cannot fit. This test deliberately ignores the intervening OFF scan and slews; it is sufficient for impossibility but need not detect every impossible schedule.
3. Otherwise coverage is **possible but uncertain**. Do not solve an unnecessary scheduling optimization or assign an arbitrary scan pair.

Conditional on the common compatible-source status, bound visit detection by \(d_j^-\le d_j\le d_j^+\). For E1–E4 under a full-ON detector interval \([p_{\min},p_{\max}]\), use \(d_j^-=p_{\min}\) for certain coverage and zero otherwise; use \(d_j^+=0\) for impossible coverage and \(p_{\max}\) otherwise. A point detector is the special case \(p_{\min}=p_{\max}\).

For E5, an otherwise eligible pair with unknown nonnegative gap has activity probability in

\[
\big[f^2e^{-b(2d)},\ f e^{-b(2d)}\big].
\]

Use the lower activity factor only for certain coverage, zero for an uncertain lower bound, and the upper factor whenever coverage is not proved impossible. Multiply these factors by \(p_{\min}\) or \(p_{\max}\) in the matching direction. Use consistent units for \(b\) and \(d\).

Combine repeated visits without assuming their independence:

\[
D_i^-=\max_{j\in\mathcal V_i}d_j^-,\qquad
D_i^+=\min\!\left(1,\sum_{j\in\mathcal V_i}d_j^+\right),
\]
\[
w_i^-=1-\zeta D_i^+,\qquad w_i^+=1-\zeta D_i^-,
\qquad
w^-=\prod_iw_i^-,\quad w^+=\prod_iw_i^+.
\]

The empty-visit/source cases give null weight one. These products use the declared independence across sources at each fixed nuisance setting; the bounds relax shared schedule and detector constraints and are therefore conservative outer bounds. Do not separately extremize alternating terms of inclusion–exclusion.

For broad Duncal uncertainty, a known masked/incompatible source remains undetectable. On an admissible source, allow detection lower bound zero. If any allowed ON time can overlap emitted radiation, allow an upper visit probability as large as one, including partial integrations; if overlap is impossible, use zero. This deliberately loose outer bound does not apply a full-integration recovery factor to an uncalibrated partial signal. The zero-response operator remains allowed, so the analytic noncontraction result needs no large Duncal simulation.

### 6.6 Strong independent-site baseline

Remove only cross-site suppression, retaining one first attempt per site and the same source-wise selection model. This isolates the effect of interaction without adding repeated independent civilizations at the same star. Call it `independent_sites`, not the continuum free process.

For each site, use its **original unconditional** first-clock distribution, speed law, emission operator, and no-birth-by-100 atom. Do not feed this oracle the interacting survival-proposal clock law. The product ratios below impose the independent model's own no-prior-arrival condition. Define

\[
e_i=\Pr(A_i>0),\quad h_i=\Pr(A_i>100),
\]
\[
n_i=\mathbb E[1_{\{A_i>0\}}w_i],\quad
j_i=\mathbb E[1_{\{A_i>100\}}w_i].
\]

Then exactly,

\[
C_{\rm ind}=\prod_i e_i,\quad
\ell_{\rm ind}=\prod_i n_i/e_i,
\]
\[
R_{\rm ind}^0=1-\prod_i h_i/e_i,\quad
R_{\rm ind}=1-\prod_i j_i/n_i.
\]

All primary emission/detector weights \(w_i(b)\) are independent of the speed mark at fixed birth time. Integrate speed out analytically. For \(\Delta=t-b\) and the uniform-\(q\) component,

\[
g_i(t,b)=\Pr(A_i>t\mid b)=
\begin{cases}
1,&\Delta\le r_i,\\
2-\Delta/r_i,&r_i<\Delta<2r_i,\\
0,&\Delta\ge2r_i.
\end{cases}
\]

For a fixed speed use \(g_i(t,b)=1\{b+r_i/v>t\}\); for S3 use its stated mixture. The first-clock density on \([-B,100]\) is \(f_i(b)=\Lambda_i'(b)e^{-\Lambda_i(b)}\), with atom

\[
p_{\infty,i}=e^{-\lambda_i(B+100k)}.
\]

For any source weight \(\omega_i(b)\), define

\[
M_i(t;\omega_i)=p_{\infty,i}+
\int_{-B}^{100}f_i(b)\,g_i(t,b)\,\omega_i(b)\,db.
\]

Then \(e_i=M_i(0;1)\), \(h_i=M_i(100;1)\), \(n_i=M_i(0;w_i)\), and \(j_i=M_i(100;w_i)\). The atom has \(A_i=\infty,w_i=1\). Thus only **one-dimensional birth-time quadrature** is required. Split at zero, fixed-speed thresholds, \(b=t-r_i,t-2r_i\), and all emission-window boundaries inside the integration domain. Do not integrate a discontinuous gate blindly. The joint speed/emission synthetic control is separate from this factorization.

Compute products in log space and use `-expm1` for \(1-\exp(x)\). Compare at matched numerical accuracy. This analytically specified baseline is stronger than merely comparing two Monte Carlo codes. A Monte Carlo implementation of the same independent-site model is a separate validation of the quadrature.

Each model must condition on its **own** survival event. Reusing interacting-survivor histories for a Monte Carlo baseline is valid only after also filtering for independent-site survival; \(E_{\rm ind}\subseteq E_{\rm accepted}\). The deterministic oracle already handles its own conditioning and avoids that extra rejection.

For a one-site ideal-silence control with \(r<B\), constant \(\lambda\), and speed-gap CDF \(F\),

\[
p(h)=\int_0^h\lambda e^{-\lambda u}F((h-u)/r)\,du.
\]

At fixed \(v\), this reduces to
\(1-\exp\{-\lambda[h-r(1/v-1)]_+\}\).
Use it to catch false application of continuum exponents.

### 6.7 Ideal-silence comparator on the same stars

For immediate persistent signatures and simultaneous perfect observation of every modeled site at zero, causal silence equals absence of all potential first attempts with \(b_i+r_i\le0\). Its probability is

\[
P(S)=\exp[-\sum_i\lambda_i(B-r_i)_+].
\]

It implies \(E\). The exact conditional likelihood given \(E\) is \(P(S)/C\). Sample the ideal-silence histories by starting each first clock at \(\max(-B,-r_i)\), using unchanged speed marks and then chronological suppression. Do not obtain these histories by rejecting rare perfect-silence cases from a large unconstrained simulation.

Report the same-star ideal-silence risk and its difference from the real/coarsened-survey risk as **observation-model sensitivity**. It is not a competitor solving the same inference problem. Its exact hard-cutoff gap and discrete tail behavior are the appropriate checks.

## 7. Uncertainty, compatibility, and range analysis

### 7.1 Independent unit and point estimates

One independent simulated universe/history is the independent unit. Stars, repeated scans, speed draws within a history, and different emission evaluations of that history are not independent experimental replicates.

For \(m\) independent histories sampled conditional on \(E\),

\[
\widehat{\ell}_{RB}=m^{-1}\sum_k w_k,\quad
\widehat{R}_{RB}=\frac{\sum_k1_{B_k}w_k}{\sum_k w_k},\quad
\widehat R^0=m^{-1}\sum_k1_{B_k}.
\]

The conditional-null estimate is unbiased; the ratio is a consistent ratio estimate, not exactly unbiased at finite \(m\). Use these lower-variance point estimates and retain the batch sums needed to diagnose their numerical stability.

### 7.2 Simple rigorous Monte Carlo intervals

Also draw \(U_k\sim U(0,1)\), independently across histories, and set \(Z_k=1\{U_k\le w_k\}\). Reuse the same \(U_k\) across variants for pairing, but never across independent histories.

- \(\sum Z_k\) out of \(m\) gives an exact binomial interval for \(\ell\).
- \(\sum 1_{B_k}Z_k\) out of \(\sum Z_k\) gives an exact conditional binomial interval for \(R\).
- \(\sum1_{B_k}\) out of \(m\) gives an exact binomial interval for \(R^0\).

Use Clopper–Pearson intervals, e.g. SciPy's documented exact option [R13]. Do not apply a binomial interval to noninteger weighted event counts. With zero null histories, report \(R\in[0,1]\); with zero arrivals, report an upper bound rather than zero. For \(n\) null histories and zero arrivals the one-sided upper bound is \(1-\alpha^{1/n}\), with \(\alpha\) adjusted for the declared multiplicity.

Before confirmation, enumerate every scalar binomial bound used for decisions. Allocate familywise Monte Carlo error **0.025** to the primary E1/Dnom/k=1 decision and **0.025** to the required robustness/diagnostic decisions, using Bonferroni within each fixed list; their combined error is at most .05. Reused identical scalar bounds need only one allocation. This includes compatibility and endpoints, and any interval-weight components used in Section 7.4. Correlation between variants does not invalidate Bonferroni. Report the actual number of bounds and per-bound error; do not multiply by the three compatibility thresholds again when they use the same bounds.

Calibration sampling uncertainty and astrophysical uncertainty are separate from this Monte Carlo error. The confidence level refers to numerical estimation under specified models, not the truth of those models.

Set the sample size from the resource calibration, using cost and the predeclared choices below, before inspecting confirmatory risks. Rejection until a fixed survivor target or a fixed attempt cap is permissible because stopping depends on the survival filter, not the conditional arrival/null outcomes. Complete the prescribed batches. A wall-clock interruption that truncates a run is not grounds to certify its interval as if it had reached the plan; treat that cell as unresolved unless a separately valid predetermined completed design is available.

### 7.3 Certified model sets and endpoint comparisons

At each \(\tau\), classify:

- **Certified retained:** \(\ell_{\rm low}\ge\tau\).
- **Certified excluded:** \(\ell_{\rm high}<\tau\).
- **Unresolved:** otherwise.

For the outer retained-risk envelope include every cell not certified excluded, using its full risk interval. For unresolved or invalid cells with no valid estimate use [0,1], unless an analytic bound narrows it. Also show the envelope supported by certified-retained cells; an empty such set is a numerical/evidence status, not proof that the family is incompatible.

To certify a material upper-envelope reduction, use the lower confidence bound on \(U_0=\max_\theta R^0_\theta\) and the upper confidence bound on \(U_{\rm post}\) over all possibly retained cells. Their difference must be at least .01, and the conservative relative reduction must be at least .25. Do not choose a favorable point estimate from a numerically ambiguous threshold crossing. Report signed differences, including increases.

If no model in a restricted family is possibly retained, report that entire family as incompatible under the convention. Do not assign it an arrival probability of zero.

An informative **negative** also needs certification. Let \(U_0\in[L_0,U_0^{\rm hi}]\), and let \(L_{\rm post}\) be the maximum risk lower bound among certified-retained models. If at least one model is certified retained, the possible absolute contraction is at most \(U_0^{\rm hi}-L_{\rm post}\), and the possible relative contraction is at most \(1-L_{\rm post}/U_0^{\rm hi}\) when \(U_0^{\rm hi}>0\). If either upper bound is strictly below its materiality threshold (.01 or .25), a material narrowing is ruled out in this family. Otherwise, failure to certify the positive criterion is **inconclusive**, not automatically a negative. If \(U_0^{\rm hi}=0\), no positive contraction is possible.

Primary comparisons across interaction-on/off use the same demographic inputs, detector information, and emission variants. Independent-site deterministic values receive quadrature-error bounds; interacting values receive Monte Carlo and numerical-error bounds. Do not compare a noisy estimate to a baseline at a materially different accuracy or with extra calibration information.

### 7.4 Valid bounds when the detector or times are only partially specified

If \(w^-\le w\le w^+\) for each history, estimate

\[
J^-=\mathbb E[1_Bw^-\mid E],\quad
J^+=\mathbb E[1_Bw^+\mid E],
\]
\[
K^-=\mathbb E[(1-1_B)w^-\mid E],\quad
K^+=\mathbb E[(1-1_B)w^+\mid E].
\]

Then the safe outer risk interval is

\[
\frac{J^-}{J^-+K^+}\le R\le
\frac{J^+}{J^++K^-},
\]

with undefined endpoint ratios replaced conservatively by 0 or 1. This may be loose because nuisance choices cannot necessarily attain every history's extreme simultaneously; it is an outer bound, not a claim that its endpoints are achievable.

Obtain Monte Carlo bounds using \(Z^\pm=1\{U\le w^\pm\}\) and the corresponding integer indicators \(1_BZ^\pm\) and \((1-1_B)Z^\pm\). Insert lower/upper binomial limits into the ratios in the conservative directions. Bound \(\ell\) with the means of \(w^-\) and \(w^+\), using their Bernoulli counterparts. A family is certainly compatible if the lower bound on the lower-null mean exceeds \(\tau\), and certainly incompatible if the upper bound on the upper-null mean is below \(\tau\); otherwise preserve possible compatibility.

Do not infer a continuous-parameter risk envelope by checking risk at the two detector endpoints. The safe weight bounds above avoid that unjustified monotonicity assumption.

### 7.5 Quantitative resolution and failure handling

Aim for 100,000 surviving histories per primary demographic ensemble. At \(\ell=.05\), that yields about 5,000 null histories on average; multiple-comparison intervals can still be roughly percentage-point scale for moderate risks. This is a planning calculation, not a guarantee of adequate precision.

If the budget cannot distinguish the material effect from uncertainty, report inconclusive evidence. Do not raise the effect threshold after seeing a result, omit a difficult model, or equate an unobserved rare event with impossibility. Exact zero is allowed only for an analytic geometric or model constraint, such as the hard-cutoff ideal-silence gap.

Every failed run retains its configuration, exception, elapsed time, backend, partial counts, and reason for exclusion from certified inference. A failed model remains unresolved in the family envelope. Numerical disagreements trigger bounded diagnosis, not selection of the more favorable implementation.


## 8. Experiments and correctness gates

Do not build the full experiment runner before the analytical and tiny controls pass. Each experiment below has a specific evidentiary purpose.

### 8.1 Required tiny controls

| Control | Expected result | Error it can detect |
|---|---|---|
| No births or fully invisible emission | \(R=R^0,\ell=1\); no-birth risk is zero | Incorrect null weighting or artificial detection |
| One source with known exponential clock | Exact quadrature agrees with simulation | Clock inversion, arrival window, conditioning |
| Common expansion speed on arbitrary small geometry | Accepted and all-candidate first Earth arrivals agree pathwise | Wrong suppression semantics |
| Two-source fast phantom | Earlier slow source suppresses faster later source | Allowing rejected candidates to expand |
| Suppressed pre-zero phantom below | Accepted survival may hold when free survival fails | Invalid mixed-speed survival shortcut |
| Same source observed twice | One shared status/emission history; joint formula matches enumeration | Double-counting targets or duty cycles |
| Two ON scans | AND behavior; never an OR probability | Misuse of injection completeness |
| ON/OFF history | Ineligible OFF-direction match cannot become a verified discovery in a synthetic selection test | Treating every hit as \(N_{\rm det}>0\) |
| Perfect survey at zero | Causal signal-silence identity; speed-independent unconditional silence | Conflating contact and radio time |
| Strict speed cutoff | Exact discrete silence gap | Importing continuum asymptotics |
| Joint fast/dark mark | Exact sign reversal from Section 4.2 | Enforcing risk reduction |
| Constant emission and duplicated source visit | Merging the physical source changes no demographic draw | Catalog pseudoreplication |
| Probability intervals | Certified outer bounds contain every small enumerated nuisance case | Invalid endpoint optimization |
| Zero simulated events | Nonzero upper bound unless analytically impossible | False numerical certainty |

Use two deterministic phantom cases:

1. \(c=1\): birth \(i\) at \(x=1,t=0,v=.1\); candidate \(j\) at \(x=1.1,t=1.1,v=.9\). The earlier source covers \(j\)'s birthplace because \(.1\le .11\). Free first arrival is \(2.322222\ldots\); accepted first arrival is 10. The earliest signal is 1 in either process.
2. Earth at zero: \(i\) at \(x=10,t=-100,v=.05\), \(j\) at \(x=8,t=-50,v=.9\). Candidate \(j\) is suppressed because \(2\le2.5\). Its hypothetical Earth arrival is \(-41.111111\ldots\), while accepted arrival is \(+100\). If \(i\)'s radio lasts one year, it has ceased crossing Earth before a survey near zero. This is a valid surviving accepted history excluded by free-arrival conditioning.

Also enumerate all marked histories on a two- or three-site **finite synthetic clock support** (two or three birth-time possibilities and two speeds per site). This finite distribution is a correctness oracle, not an approximation asserted to represent the continuous scientific model. Compare scalar and batched engines, exact weighted ratios, and any conditional sampling shortcut with the enumerated truth.

For independent-site quadrature, initially target absolute probability error \(10^{-8}\) and relative error \(10^{-6}\) when the probability exceeds \(10^{-6}\). Refine split quadrature or use arbitrary precision on a small subset; accept the numerical contribution only when it is below \(10^{-4}\) absolute for every main reporting cell and well below its statistical uncertainty. These tolerances are comfortably below the .01 effect threshold. Do not treat an integrator's internal error estimate alone as validation.

### 8.2 Bounded continuum reference experiment

Use \(d=3,T=c=1,\lambda\nu_3=1\) and \(F(q)=q^\alpha\) on \(0<q<1\), with \(\alpha\in\{.5,1,2,3,4,6\}\). Check \(h\in\{10^{-2},10^{-4},10^{-6},10^{-8}\}\) by stable quadrature, and \(10^{-12}\) only with adequate arbitrary precision.

Verify:

- The exact kernel against a direct radial integral on ordinary-scale cases.
- \(b(h)=\tfrac34h^2+\tfrac12h^3\) for \(\alpha=1\).
- \(b(h)=h^3-\tfrac14h^4\) for \(\alpha=2\).
- The repaired warning formula and \(b'(h)=L(h,1)\).
- Ratios to each asymptotic leading term; preserve the slow logarithmic convergence at \(\alpha=3\).
- The finite-moment cutoff case and at least one atomic speed law.

Require relative agreement of independently evaluated ordinary-scale formulas within \(10^{-9}\), and high-precision convergence when requested tolerances make binary64 unreliable. Do not demand agreement with the limiting law to \(10^{-9}\) at finite \(h\); truncation error and floating-point error are different.

Implement an exact finite-shell interaction check for **\(\alpha=1,\ h=.02,.5\)**, at most 10,000 conditional histories each. No vast spatial box or grid is needed. Conditional on ideal silence, sample independent restrictions to \(B_h\) and \(C_h\setminus B_h\):

1. Compute \(b,s\).
2. Draw \(N_B\sim\operatorname{Poisson}(b)\mid N_B\ge1\) and \(N_{C\setminus B}\sim\operatorname{Poisson}(s-b)\). Do not repeatedly sample an ordinary Poisson until it is positive. For these two settings \(b\le .25\); invert the truncated CDF using \(p_1=b/\operatorname{expm1}(b)\), \(p_{k+1}=p_kb/(k+1)\), and one open-interval uniform. If accumulated probabilities are numerically ambiguous, recompute at higher precision rather than truncating the random count. If \(b=0\), the conditional experiment is undefined and must not run.
3. A point uniform in the shell intensity can be sampled by
   \(D=[T^{d+1}+U((T+h)^{d+1}-T^{d+1})]^{1/(d+1)}\),
   \(z=D U'^{1/d}\), \(r=cz\), \(t=D-z\), an independent uniform direction on the sphere, and the declared speed mark.
4. Rejection from this shell sampler obtains a \(B_h\) point when \(D+qz\le T+h\), and a complementary point otherwise. This is cheap enough for the stated \(\alpha,h\), but is not authorized at tiny horizons or high \(\alpha\).
5. Sort all sampled points and apply chronological suppression. Compute the free contacting source's own signal, the first accepted signal, and accepted physical arrival separately. When no accepted point arrives by \(T+h\), record \(H>h\) as right-censored. Do not use the earliest later arrival among shell points as the global later arrival: sources outside the shell may win after this horizon.
6. Estimate
   \(p_T(h)=(1-e^{-b})\Pr(H\le h\mid N_B\ge1,S_T)\).
   Compare its interval with the rigorous bounds in Section 3.2.
7. Compare the free sample, conditional on \(N_B\ge1\), with the exact finite-horizon joint and marginal formulas in Section 3.3. For accepted normalized warnings, use only histories with accepted \(H\le h\), and display finite-horizon qualifications. Global first-signal warning and the free contacting source's own warning are distinct statistics; only their limiting relation is supplied by the theorem.

Use the deterministic phantom controls to guarantee that rejection logic is exercised; absence of suppressed events in a small random sample does not validate that branch. Do not fit a theorem exponent to a handful of noisy rare events. Numerical reference agreement is consistency evidence; the proof supplies the asymptotic guarantee.

### 8.3 Minimal comparison matrix

The rows below define the permitted confirmatory workload. A control need not be repeated when an exact identity already resolves it.

| Experiment | Inputs | Comparisons | Question resolved |
|---|---|---|---|
| Core conditional audit | 16 demographics, \(k=1\), E1, Dnom | Interacting; independent-site exact; same-star perfect silence | Does the instrument-conditioned upper envelope materially narrow? |
| Emission sensitivity | Same 16, \(k=1\), E2–E5 and analytic E0 | Reuse histories; same detector scenarios | Which visibility assumptions create apparent information? |
| Detector sensitivity | E1–E5 at \(k=1\); Dweak, Dhigh, Dpositive, Duncal | Point scenarios plus conservative continuous bounds | Does a claimed constraint require an unverified calibration lower bound? |
| Future continuation | Same 16 prefixes, \(k=0,10\), E1 and E0 only | Dnom/Dweak/Dhigh and interval bounds for E1 | Is the forecast driven by assumptions after the survey? |
| History boundary | Four ensembles in Section 5.1, E1, \(k=1\) | Interacting and exact independent, three detector scenarios | Is the finite starting age influential? |
| Same-star ideal reference | 16 primary demographics; future \(k=0,1,10\) reused | Exact silence conditioning and geometry controls | Where does the ideal observation differ? |
| Numerical calibration | Representative low/high activity histories | Scalar versus batched, same draws and accuracy | Is laptop execution feasible and correct? |

Do **not** silently claim the future-rate controls cover every cross-combination with intermittent or finite-life emission. This is a deliberately limited one-factor-at-a-time robustness design; the complete uncertainty family beyond the evaluated combinations remains broader. State which envelope each plot summarizes.

Include an analytic/one-site positive control with substantial survey updating and the sign-reversal control. This establishes that an apparently weak survey effect is not merely an insensitive estimator. The positive control can use a synthetic prior with .5 probability of a near-term bright arrival and .5 probability of no source; a .94 detector gives \(\ell=.53\), \(R^0=.5\), \(R=.03/.53\approx .0566038\). Both histories must satisfy no previous arrival.

Do not compare to published transmitter-prevalence percentages as if they measured physical arrival. Include the published binomial prevalence formula only as a limiting selection-code check:
\((1-f_{\rm TX}\eta D)^n\) for independent, single-opportunity sources under its own assumptions [R2]. The strong scientific baseline is the matched finite-site quadrature above.

## 9. Resource budgets and evidence gates

### 9.1 Hard ceilings and actual-machine inspection

Inspect `uname -m`, `sw_vers`, physical memory, free disk space, Python version, NumPy/SciPy versions and build information, CPU availability, and any active power-saving restrictions. Confirm an ARM64-native Python when possible; record emulation if used. Do not infer RAM or backend precision from “M3 Max.”

Use CPU binary64. Do not silently route work to MPS, change to float32, or offload computation. No cloud compute, CUDA, paid computation, services, or proprietary data is needed.

Hard limits:

| Resource | Cumulative limit |
|---|---|
| Local experimental compute and result generation | **6 wall-clock hours**, including development trials, failed runs, compilation, repairs, and optional acceleration |
| Network/data acquisition | **60 minutes elapsed** and **5.0 GB downloaded**; ordinary source/metadata downloads included |
| Peak process RSS | \(\min(8\ {\rm GiB},0.25\times\text{physical RAM})\) |
| Total project disk use | **8 GiB**, also requiring at least 4 GiB free beyond the planned footprint |
| Generated results/checkpoints | **1 GiB**; summarize histories, do not dump every trajectory |
| Simulated candidate universes | **60 million**, including discarded survival-proposal histories, pilot, controls, and repairs |
| Per mixed-speed demographic ensemble | **12 million attempted universes**, and never beyond remaining global budget |
| Primary survivor target | **100,000** per demographic ensemble; permitted cost-only fallback **25,000** |
| History-age diagnostic survivor target | **25,000** each |
| Ideal-silence reference target | **25,000** per primary demographic setting, reusing futures |
| Continuum shell reference | **20,000** conditional histories total |
| Development/calibration/pilot jobs | At most **30** launches total |
| Confirmatory demographic ensembles | **20** interacting demographics plus **16** ideal-silence ensembles |
| Derived reporting cells | At most **2,000**; pre-enumerate and hash the matrix |
| Repair budget | **30 minutes compute**, at most two targeted repairs per failed gate; included in 6 hours |

The local wall-clock ledger sums jobs even if run concurrently; parallel execution does not create extra budget. Dependency installation/network transfers use their separate allowance, but local build/test computation counts. Avoid a full archive download if disk reserve is insufficient; take the coarsened fallback.

Implementation and analysis effort are separate from simulation runtime. A planning estimate is 4–8 focused hours for implementation, review, and interpretation plus 2–6 hours of local computation, with overlap possible; roughly 8–16 hours end to end if access and dependencies cooperate. These are unmeasured estimates, not an M3 performance claim. An early analytic or data-limited outcome should take much less.

### 9.2 Stage decisions

| Stage | Question and minimum work | Local time allocation | Evidence and decision |
|---|---|---:|---|
| G0: constructive feasibility | Inspect machine; validate target rows; try metadata/schedule access; derive first-clock and dark-family identities | 10 min, plus bounded network allowance | Continue exact survey only with a reconciled schedule. Otherwise declare F1/F2 and continue unaffected work. Missing geometry with no usable Appendix B is a blocker for empirical geometry claims. |
| G1: tiny correctness | Scalar engine, one-site formulas, finite enumeration, phantom controls, linked detector, stable theorem kernel | 20 min | Every exact invariant passes; independent probability calculations meet Section 8 tolerances. Repair within pool; if still wrong, stop comparisons and report invalid experiment. A proven theorem defect is documented separately. |
| G2: resource calibration | Representative batches at \(\mu=1,12\), S1/S3/S4; small S4 age-diagnostic batches; scalar/batched equality; measure survival frequency, throughput, RSS | 10 min | Project total cost with 2× safety factor. Select 100k or 25k survivor target using only cost/precision planning, then freeze. If neither fits, complete analytic/data audit and classify intended comparison infeasible/inconclusive. |
| G3: mechanism pilot | Fresh development seeds; two demographic cases, positive/null/sign controls; small continuum shell check | 20 min | Verify detection of known synthetic effects and correct uncertainty. A noisy empirical pilot is not a rejection of the hypothesis. Freeze protocol and confirmation seeds after repairs. |
| G4: locked comparison | Core 16 demographics, exact independent baseline, primary detector/emission evaluations | 190 min | Run fixed design. Preserve all cells, including unresolved ones. No outcome-based tuning, extra rate points, or dropped difficult cases. |
| G5: declared robustness | Continuation replays, four age diagnostics, ideal-silence references, continuous-weight bounds | 45 min | Resolve only declared sensitivities. Unfinished mandatory robustness narrows the conclusion; it cannot be replaced by favorable optional checks. |
| G6: diagnosis/report | Validate tables/plots, uncertainty coverage, provenance, result labels, regeneration commands | 35 min reserved | Deliver the justified outcome at the achieved evidence level. Preserve failures and blocked inputs. |
| Bounded repair pool | Specific code/data/numerics corrections | 30 min | Never resets a stage or total cap. Any scientific protocol change is exploratory and requires unused confirmation evidence. |

These allocations sum to six hours. Unused earlier time may support a later required stage, while the last 35 minutes remain reserved for reporting. Stop new simulations before that reserve is consumed.

### 9.3 Calibration, scaling, and resizing rules

Run 1024 then 4096 and, if feasible, 16384 attempted histories for low/high activity. Time one cold process including imports and three warmed batches with identical fixed work. Use `time.perf_counter` for workload timing, and report imports, geometry/data preparation, clock generation, suppression, likelihood evaluation, baseline quadrature, and report generation separately. Record raw timings and peak RSS with macOS `/usr/bin/time -l` or a verified process monitor; account for its units.

There is no hardware-speedup research claim. These timings test feasibility. If optional batching/acceleration is reported as faster, compare identical histories, outputs, precision, thread settings, and batch sizes; include setup/compilation separately.

Estimate mixed-speed cost from actual survivor frequency with a conservative lower confidence bound, not from a noisy point estimate alone. Estimate cost of each detector pass on already-surviving histories. Include the independent quadrature and repeated-source likelihood, not only event propagation.

Choose 100k survivors only if the projected full required matrix with a 2× cost margin fits the unspent wall-clock budget AND the per-cell/global proposal ceilings. Include the fixed 50k-proposal survival diagnostics in this projection. Otherwise use the predeclared 25k target for the primary ensembles and clearly state the reduced resolution. Do not alter the model grid or decision threshold. Process mixed-speed cells in a fixed round-robin schedule so every cell receives an initial tranche before one difficult cell consumes its cap. The exact lower-speed-cone proposal, common-speed shortcut, and ideal-silence sampler remain available regardless of rare unconditional survival.

If memory exceeds the ceiling, reduce batch size, not number of stars or numerical precision. If resource projection fails even at 25k, retain analytic controls and any valid completed cells, use conservative outer envelopes, and stop. Do not shrink to a conveniently nearby subset of stars.

### 9.4 Exploration versus confirmation

Use development seeds derived from `SeedSequence([20261101,0,...])` and confirmation seeds from `SeedSequence([20261101,1,...])`. Give every demographic ensemble and stage a stable integer ID. Record the generator type and NumPy version; do not depend on Python's randomized hash.

Freeze the following in `protocol.lock.json` before confirmation: target and schedule hashes, fallback grade, parameter sets, detector bounds, experiment list, sample-size choice, attempt caps, tolerances, uncertainty allocation, seeds, stopping rules, and effect thresholds. Data quality and calibration checks may inform the freeze; arrival-probability comparisons may not determine the scientific grid.

Shared histories across variants are deliberate paired evidence. Use independent confirmation draws after debugging. A material post-freeze scientific change requires a dated deviation entry and fresh confirmation within the original remaining budget. If that is impossible, label the changed analysis exploratory.

## 10. Repository, interfaces, and commands

Use ordinary Python scripts and local JSON/CSV/NPZ files. No database, notebook-only workflow, web dashboard, or orchestration service is needed.

### 10.1 Minimal structure to create

| Path | Responsibility |
|---|---|
| `README.md` | Exact setup, short usage, data grade, main conclusion, reproduction commands |
| `pyproject.toml`, `requirements.lock.txt` | Small package and resolved dependency versions |
| `config/protocol.json` | Scientific choices from this brief and budgets |
| `inputs/` | Theorem PDF if supplied; immutable retrieved source metadata |
| `data/targets.csv`, `data/visits.csv` | Normalized sites and schedule, with provenance/status |
| `src/seti_audit/data.py` | Streaming acquisition, catalog reconciliation, interval fallback |
| `src/seti_audit/model.py` | First clocks, marks, scalar/batched suppression, future replay |
| `src/seti_audit/detection.py` | Retarded-time gates, linked visits, CTMC formulas, null bounds |
| `src/seti_audit/oracles.py` | Independent-site quadrature, common-speed/silence identities, tiny enumeration |
| `src/seti_audit/theorem.py` | Stable kernel, repaired warning expression, shell sampler |
| `src/seti_audit/inference.py` | Weighted point estimates, Bernoulli audit draws, intervals, envelopes |
| `src/seti_audit/cli.py` | Small command-line interface and cumulative budget ledger |
| `src/seti_audit/__init__.py`, `src/seti_audit/__main__.py` | Package initialization and entry point dispatching to the CLI, so `python -m seti_audit` works |
| `tests/` | Scientific correctness controls, not tests that merely restate implementation |
| `results/` | Append-only run manifest, counts, timings, failures, protocol lock, tables |
| `report/REPORT.md`, `report/figures/` | Findings with assumptions, evidence, and reproducible figures |

These module boundaries are engineering suggestions; you may combine files without changing scientific interfaces or outputs.

Required callable contracts:

```text
load_catalog(...) -> targets, geometry, provenance
load_schedule(...) -> exact_visits OR bounded_visits, data_grade
sample_first_clocks(config, rng, conditioning) -> clocks, speeds, marks
simulate_history(clocks, speeds, geometry, intersite) -> history
null_weight(history, visits, emission_config, detector_config) -> w or (w_min,w_max)
independent_oracle(config, visits) -> C, likelihood, R0, R, error_bounds
summarize(counts, protocol) -> per_cell_intervals, model_statuses, envelopes
```

Store one sampled history in a compact dataclass/array representation. Do not create object graphs or per-event Python objects in million-history batches. Retain a small deterministic replay sample and representative failures; batch totals and seeds are enough for most successful trials.

### 10.2 Dependencies and intended command sequence

Use a recent supported native Python, preferably 3.12 if available, with `numpy, scipy, matplotlib, pytest`. Add `mpmath` for the tiny high-precision checks. Standard-library `csv, json, urllib, hashlib, datetime, pathlib` suffice for input handling. Do not install CUDA packages. The exact versions and Apple wheels have not been verified on the target Mac: test import and numerical behavior, then freeze successful versions. If a dependency cannot be installed, complete analytical work and identify the precise blocked component.

The following are **interfaces you must implement**, not commands already verified to exist:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy scipy matplotlib pytest mpmath
python -m pip install -e .
python -m pip freeze > requirements.lock.txt

python -m seti_audit env --out results/environment.json
python -m seti_audit acquire --config config/protocol.json
python -m seti_audit validate-data --config config/protocol.json
python -m pytest -q
python -m seti_audit theorem-check --config config/protocol.json
python -m seti_audit calibrate --config config/protocol.json
python -m seti_audit pilot --config config/protocol.json
python -m seti_audit freeze --config config/protocol.json
python -m seti_audit run --protocol results/protocol.lock.json
python -m seti_audit report --protocol results/protocol.lock.json
```

Create a `smoke` subcommand completing one tiny target history, linked likelihood, interval, and report row in under a minute after setup. Also support `report --from-results` that regenerates essential tables and plots without simulation, and `run --resume` that preserves seeds, completed batches, scientific protocol, and the cumulative ledger. Resume must never rerun until a favorable outcome occurs.

Do not use placeholder data when acquisition fails. `acquire` must select the declared fallback grade or report a precise blocker.

## 11. Required report and outcome interpretation

Lead the report with the research decision and its evidence grade. Include:

1. The exact horizon definition and actual or interval-valued \(t_0\); physical arrival must remain distinct from radio reception.
2. Catalog identity resolution and the treatment of the repeated target.
3. A concise assumption ledger: measured survey information versus population, emission, detector-transfer, and continuation assumptions.
4. The theorem audit, repaired formula, missing original scripts, and independent checks actually completed.
5. The per-model table: configuration ID, \(C,\ell,R^0,R\), intervals, compatibility status at each threshold, attempted/surviving/null/arrival counts, detector/data grade, and failures.
6. \(I_0,I_{\rm select},I_{\rm post}\) for each named family, with certified and possible retained sets. Include the full-dark analytic result.
7. Interaction-on/off differences and the same-star ideal-silence comparison, with uncertainty.
8. Continuation and history-boundary effects; no interpretation as a measured future rate.
9. Actual local time, memory, disk, package/backend/precision, and the cumulative cost of failed/exploratory work.
10. Specific limits of the conclusion and at most one high-value next step.

Essential figures are: risk envelopes before/after the null by named emission/detector family; \(\ell\) versus \(R\) with compatibility thresholds and uncertainty; the same-star ideal-silence discrepancy; and the theorem's exact/leading ratios showing the critical logarithmic regime. Generate static plots suitable for export, with source/configuration IDs. Tables may replace a plot when there are too few resolved values.

Use these outcome categories per claim, not one label hiding different components:

| Category | Required basis |
|---|---|
| **Supported contribution** | Correctness controls and adequate precision support the prespecified conditional claim or a useful verified information limit |
| **Informative negative result** | Valid comparison rejects material narrowing in the stated family, or a verified analytic obstruction rules out the proposed inference |
| **Practical infeasibility** | Measured cost or supported scaling prevents the intended resolution within limits |
| **Inconclusive evidence** | Missing calibration/schedule, interval width, limited family coverage, or budget leaves the decision unresolved |
| **Invalid experiment** | A code, data, baseline, or measurement defect prevents interpretation |

The analytic dark-family result can be supported while the exact survey-calibrated numerical question remains inconclusive. A positive conditional result under Dnom is not evidence that Dnom accurately describes the telescope for arbitrary civilizations. A timeout is not a refutation. A simulation matching the theorem is not a proof of its empirical applicability.

### 11.1 Final artifact contract for stages reached

Deliver runnable code and usage instructions for implemented stages; the frozen configuration and provenance; raw aggregate results and failed-run records; essential tables/figures; and `report/REPORT.md`. Include a compact machine-readable `conclusions.json` with claim, outcome category, evidence IDs, scope, and unresolved dependencies.

For an analytic early stop, deliver the derivation/counterexample, a minimal replay or symbolic/numeric check if implemented, and the reason later benchmarks are unnecessary or blocked. Do not manufacture a large codebase to satisfy an inapplicable benchmark requirement.

A successful completion includes a justified early stop. Execute ordinary repairs and all authorized unaffected stages autonomously. If exact survey reconstruction remains blocked, identify the smallest missing schedule/calibration input, finish the fallback, and report what was actually learned.

## 12. Research coverage and claim-to-evidence map

The literature search used both general and stronger-coverage search engines, primary full-text papers, author-hosted material, the survey's archive metadata, and official technical documentation. Queries covered SETI null likelihoods, physical arrival/contact, incomplete coverage, expanding civilizations, Johnson–Mehl/Avrami growth, random-speed phantom births, Poisson thinning, and observation/behavior identifiability. Backward references and relevant newer work were followed where they changed the design. Search date: **2026-11-01**.

| Central claim | Evidence/status | Remaining uncertainty and resolving action |
|---|---|---|
| Ideal silence has a speed-independent likelihood | [R1, Lemma 2/E5]; related prior art [R5, Section IV.E] | Recheck causal inequality and exact controls |
| Accepted early-contact asymptotics agree with free leading order | [R1, Theorem 1/Lemma 3] | Finite-horizon error remains; use exact bounds |
| Source warning display needs repair | Rendered PDF p. 8; planning derivation in Section 3.3 | Check independent integral and derivative |
| Published scripts were not supplied | Attachment inventory | Implement fresh bounded checks; never claim their reproduction |
| A finite survey null is not no Earth-crossing signal | [R2–R4], [R7–R8] | Requires explicit observing/selection likelihood |
| Incomplete-survey expansion inference is already prior art | [R6, Eqs. 14–20] | Novelty restricted to this instrument-specific audit |
| Random-speed free growth differs from accepted growth | [R1], [R10, introduction/Eqs. 1.1–1.2] | Pathwise phantom controls |
| First attempts suffice at permanent fixed sites | Planning proof, Section 6.2 | Exhaustive tiny enumeration; fails with rebirth |
| Independent-site baseline factorizes | Planning conditional-product derivation, Section 6.6 | Quadrature checked against enumeration and MC |
| Full-dark counterparts prevent envelope contraction | Planning inclusion proof, Section 4.3 | Assumption is the presence of those counterparts; does not give universal [0,1] |
| Null conditioning can increase risk | Covariance identity and exact synthetic control | Do not impose monotonic posterior risk |
| 62 published rows appear to represent 61 sites | Parsed Appendix A, duplicate TOI 1730.01 | Reconcile with exact logs |
| Injection hits do not independently calibrate full verification | [R2, Section III.7/IV.2/Table 2] and selection audit | Need paired injection outcomes or retain nuisance bounds |
| Exact endpoint/schedule unavailable during planning | Archive access attempts; [R3] metadata | Ordinary download or F1, no fabricated scan times |
| M3 runtime is unknown | No target-hardware experiment performed | G2 cost calibration |

The recent 2026 UCLA overview [R12] does not change the selected data cutoff. Grimaldi's 2026 paper [R8] explicitly uses “contact” for an electromagnetic intersection; its subject must not be confused with this project's physical expansion. The random-speed exposed-point central limit theorem [R10] concerns a different free-growth statistic and does not supply a theorem for this accepted finite-site inference.

A close 2026 Drake–Fermi–Brin computational-framework paper [R14] was investigated further after initial browser decoding failures. Its public 25-page supplement was recovered, and the relevant model and observation sections were read. It already gives a general completeness function, a conditional product null likelihood, and MWA Vela reweighting (Sections S5.5–S5.14). Its coarse settlement/silence model and reduced application do not implement the specific finite-site, causally suppressed century-arrival calculation specified here. That is a scoped comparison of inspected content, not an exhaustive novelty claim.

## 13. Pre-delivery adversarial review

Before reporting your result, repeat three distinct passes and record only material findings and dispositions:

1. **Mathematics and novelty:** recheck conditioning, finite-age support, phantom suppression, repaired source formula, matched baseline, and limits of prior-art claims.
2. **Experiment:** try to explain any apparent narrowing by deleting high-risk unresolved cells, using a stronger detector, retuning parameter ranges, double-counting observations, falsely independent emission states, or numerical underflow. Check that a null can increase risk and that a weak/missing effect is distinguishable from insufficient resolution.
3. **Execution:** replay setup from a clean project, inspect dependency and data availability, verify commands, budgets, restart behavior, hashes, and report regeneration.

This brief was itself subjected to distinct mathematical/novelty, experimental, and execution reviews, with affected portions rechecked after repair:

| Review | Material findings | Disposition |
|---|---|---|
| Mathematics and novelty | Incomplete page-8 display; missing claimed scripts; invalid own-mark survival shortcut for mixed speeds; existing generic survey-likelihood prior art | Independent formula and checks; explicit unperformed reproduction; proved lower-speed-cone sampler; novelty narrowed to the scoped physical-arrival audit |
| Experimental | Initial rate grid could not exclude any model; a null can raise risk; invisible counterparts prevent contraction; noisy threshold crossings could manufacture a conclusion | Grid changed analytically before arrival comparison; exact controls and inclusion proof; separate positive, negative, and inconclusive certification rules |
| Execution and empirical fidelity | Duplicate target; unavailable exact timing and final calibration; frequency mask versus hit-efficiency mismatch; unnecessary nested quadrature | One site with linked visits; constructive F1/F2; explicit admissible class and transfer assumptions; analytic speed integration and fixed cumulative budgets |

No full PoC or M3 benchmark was performed during this planning work. Any new fixable defect must be repaired within the bounded allowance. The unresolved empirical uncertainties remain explicit assumptions, early gates, or blockers.

Stress outcomes have predetermined dispositions: a nonconstructive or incorrect theorem cannot validate the reference but need not invalidate independently derived finite-site formulas; an inaccessible schedule triggers F1; a missing final detector calibration triggers F2; a known mechanism narrows novelty; favorable synthetic-only success is not an empirical contribution; a stronger exact baseline removing an effect is reported; excessive cost triggers scope-qualified infeasibility; and a false primary hypothesis is a legitimate negative result.


## Appendix A. References and precise source locations

**[R1] Supplied mathematical research note, author not identified (1 November 2026).** *Silence, expansion speed, and a Dirichlet law for early contact.* Attachment: `silence_contact_theorem.pdf`; handoff path `inputs/silence_contact_theorem.pdf`; original path and SHA-256 in Section 2.1. Definitions: p. 2. Theorem 1/E1–E4: p. 3. Lemmas 2–3: pp. 4–5. Pair intensity and regular variation/E8–E9: pp. 6–7. Exact kernel/E10: pp. 7–8. Damaged warning display and closed forms: p. 8. Claimed computations: pp. 9–10. Varying-rate extension/E11: pp. 10–11. Discrete counterexamples and limitations: pp. 11–12. Originality discussion: pp. 12–13. No public DOI or named author appears in the supplied note.

**[R2] Margot, Jean-Luc; Li, Megan G.; Pinchuk, Pavlo; Myhrvold, Nathan; Lesyna, Larry; et al. (2023).** *A Search for Technosignatures Around 11,680 Stars with the Green Bank Telescope at 1.15–1.73 GHz.* The Astronomical Journal **166**, 206. [DOI: 10.3847/1538-3881/acfda4](https://doi.org/10.3847/1538-3881/acfda4). Version inspected: [arXiv:2308.02712v4, 16 October 2023](https://arxiv.org/html/2308.02712v4). Critical locations: Section II; Sections III.4–III.7; Section IV.2/Table 2; Section V.2/Eqs. 13–15; Appendix A/Tables 5–6 (PDF pp. 18–19). Primary article and tables were accessed.

**[R3] Margot, Jean-Luc; Li, Megan G.; Pinchuk, Pavlo; et al. (2025).** *Data from: A Search for Technosignatures Around 11,680 Stars with the Green Bank Telescope at 1.15–1.73 GHz.* Dryad dataset, version 370211, 13 June 2025. [DOI: 10.5061/dryad.wm37pvn0b](https://doi.org/10.5061/dryad.wm37pvn0b). [Landing page and README schema](https://datadryad.org/dataset/doi:10.5061/dryad.wm37pvn0b). Landing page, metadata, and schema were inspected; candidate CSV contents were not downloaded during planning. File hashes are in Appendix C.

**[R4] Sheikh, Sofia Z.; Huston, Macy J.; Fan, Pinchen; Wright, Jason T.; Beatty, Thomas; Martini, Connor; Kopparapu, Ravi; Frank, Adam (2025).** *Earth Detecting Earth: At what distance could Earth's constellation of technosignatures be detected with present-day technology?* The Astronomical Journal **169**, 118. [DOI: 10.3847/1538-3881/ada3c7](https://doi.org/10.3847/1538-3881/ada3c7). [Full text, arXiv:2502.02614v1](https://arxiv.org/html/2502.02614v1). Abstract and Sections I–II support signal-class-specific detectability, not a physical-arrival model.

**[R5] Olson, S. Jay (2015).** *Homogeneous cosmology with aggressively expanding civilizations.* Classical and Quantum Gravity **32**, 215025. [DOI: 10.1088/0264-9381/32/21/215025](https://doi.org/10.1088/0264-9381/32/21/215025). [Full text, arXiv:1411.4359v2](https://arxiv.org/pdf/1411.4359v2). Section IV.E, Eqs. 24–26, treats observability conditional on non-saturation and common-light-speed visible domains; Section IV.F discusses boundaries. Relevant full-text sections were read.

**[R6] Olson, S. Jay; Ord, Toby (2021).** *Implications of a search for intergalactic civilizations on prior estimates of human survival and travel speed.* [arXiv:2106.13348v2](https://arxiv.org/pdf/2106.13348v2). Sections II–IV, especially Eqs. 14–20, combine expanding-civilization models, a detection fraction, a null result, and Self-Indication-Assumption updating. Different population, observer assumptions, and inferential target from this PoC.

**[R7] Grimaldi, Claudio; Marcy, Geoffrey W. (2018).** *Bayesian approach to SETI.* Proceedings of the National Academy of Sciences **115**, E9755. [DOI: 10.1073/pnas.1808578115](https://doi.org/10.1073/pnas.1808578115). [Full text with supplementary material, arXiv:1810.01207v1](https://arxiv.org/pdf/1810.01207v1). Section II.B/Eqs. 5–11 specifies detection/luminosity factors; Section III/Eqs. 13–15 gives null and detection likelihoods. This concerns electromagnetic signals, not interacting expansion arrival.

**[R8] Grimaldi, Claudio (2023; 2026).** Two related primary papers:

- *Inferring the rate of technosignatures from 60 yr of nondetection.* The Astronomical Journal **165**, 199 (2023). [DOI: 10.3847/1538-3881/acc327](https://doi.org/10.3847/1538-3881/acc327); [arXiv:2301.07165v2](https://arxiv.org/pdf/2301.07165v2). Sections 1 and 3 explicitly consider no signal crossings; Section 3.2/Eq. 7 concerns waiting for radio crossing.
- *Undetected Past Contacts with Technological Species: Implications for Technosignature Science.* The Astronomical Journal **171**, 154 (2026). [DOI: 10.3847/1538-3881/ae394b](https://doi.org/10.3847/1538-3881/ae394b); [arXiv:2602.17736v1](https://arxiv.org/html/2602.17736v1). Introduction and Section II define “contact” as a signal intersection; Sections II–III examine undetected crossings and detectability. Do not translate their terminology into physical colonization.

**[R9] Last, Günter; Penrose, Mathew (2017).** *Lectures on the Poisson Process.* Author manuscript dated 21 August 2017. [Author-hosted full text](https://stoch.math.kit.edu/img/Last/lastpenrose2017.pdf). Theorem 3.9 and Eq. 3.5, printed pp. 23–25: Laplace/PGFL formulas. Theorem 5.6, printed p. 42: marking. Theorem 5.8 and Corollary 5.9, pp. 43–44: independent thinning. Relevant sections were inspected; dependent accepted births are not an independent thinning by assertion.

**[R10] Bhattacharjee, Chinmoy; Molchanov, Ilya; Turin, Riccardo (2024).** *Central limit theorem for a birth-growth model with Poisson arrivals and random growth speed.* Advances in Applied Probability **56**, 1004–1032. [DOI: 10.1017/apr.2023.58](https://doi.org/10.1017/apr.2023.58); [arXiv:2107.06792v4](https://arxiv.org/pdf/2107.06792v4). Introduction, Eqs. 1.1–1.2 and discussion immediately following, explicitly distinguish exposed points/free random-speed fronts from suppression by accepted seeds.

**[R11] Pinchuk, Pavlo; Margot, Jean-Luc; Greenberg, Adam H.; et al. (2019).** *A Search for Technosignatures from TRAPPIST-1, LHS 1140, and 10 Planetary Systems in the Kepler Field with the Green Bank Telescope at 1.15–1.73 GHz.* The Astronomical Journal **157**, 122. [DOI: 10.3847/1538-3881/ab0105](https://doi.org/10.3847/1538-3881/ab0105). [Author-hosted PDF](https://seti.ucla.edu/jlm/publications/Pinchuk19.aj157.technosignatures.pdf). Sections 3.4–3.5, Table 2, and Appendices B–C document filtering and inherited interference bands. This is prior-method evidence, not direct 2020–2023 calibration.

**[R12] Margot, Jean-Luc (2026).** *Results of ten years of UCLA SETI searches with the Green Bank Telescope.* IAU Symposium 404 proceedings preprint. [arXiv:2605.05408v1, 6 May 2026](https://arxiv.org/html/2605.05408v1). Sections 2, 5–6, and 10 were inspected for propagation, efficiency, and data archival. It does not replace the chosen 2020–2023 dataset.

**[R13] SciPy contributors (documentation accessed 1 November 2026).** *BinomTestResult.proportion_ci.* [Official documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html). The `method="exact"` option uses Clopper–Pearson intervals. Original reference: Clopper, C. J.; Pearson, E. S. (1934), *The use of confidence or fiducial limits illustrated in the case of the binomial*, Biometrika **26**(4), 404–413. Verify the installed API before relying on it.

**[R14] Gams, Matjaž; Kosanović, Aleksander; Stopar, Julija (2026).** *General Probabilistic Computational Framework Applied to Drake–Fermi–Brin Models of Technological Civilizations.* Computation **14**(8), 181, published 7 August 2026. [DOI: 10.3390/computation14080181](https://doi.org/10.3390/computation14080181). [Supplementary materials, Zenodo v1](https://doi.org/10.5281/zenodo.21705348). Main-article access was partly limited, but its accessible content and the recovered 25-page supplement were used. Relevant supplement locations: Section S1.2 (coarse settlement/silence model); Sections S5.5–S5.9, Eqs. S38–S54 (completeness, Poisson/product null likelihoods and reweighting); Section S5.14 (MWA Vela application). This is close prior art for an observation layer and scenario reweighting, not evidence of a matched UCLA physical-arrival calculation.

## Appendix B. Embedded primary-target transcription

The CSV below is a planning transcription of [R2, Appendix A, Tables 5–6], included so the handoff can recover geometry without this conversation. Preserve the two rows for TOI 1730.01 in the **visit-row** table, but merge their physical birthplace. A `year_group` is not an exact visit year. Validate against the source and logs before scientific confirmation. Do not treat source-row labels as extra stars.


```csv
source_row,year_group,TOI,distance_pc,RA_hms,Dec_dms
1,2020-2021,469.01,68.19,06:12:13.88,-14:38:57.54
2,2020-2021,479.01,194.55,06:04:21.53,-16:57:55.4
3,2020-2021,488.01,27.36,08:02:22.47,03:20:13.79
4,2020-2021,536.01,844.06,06:30:52.9,00:13:36.82
5,2020-2021,546.01,726.41,06:48:46.71,-00:40:22.03
6,2020-2021,561.01,85.80,09:52:44.44,06:12:57.97
7,2020-2021,562.01,9.44,09:36:01.79,-21:39:54.23
8,2020-2021,571.01,405.24,09:01:22.65,06:05:49.5
9,2020-2021,652.01,45.68,09:56:29.64,-24:05:57.07
10,2020-2021,969.01,77.26,07:40:32.8,02:05:54.92
11,2020-2021,1235.01,39.63,10:08:52.38,69:16:35.83
12,2020-2021,1243.01,43.19,09:02:55.83,71:38:11.1
13,2020-2021,1718.01,52.30,07:28:04.33,30:19:18.24
14,2020-2021,1726.01,22.40,07:49:55.05,27:21:47.28
15,2020-2021,1730.01,35.69,07:11:27.8,48:19:40.56
16,2020-2021,1732.01,74.76,07:27:12.35,53:02:42.97
17,2020-2021,1766.01,210.25,09:54:34.35,40:23:16.6
18,2020-2021,1774.01,53.97,09:52:38.86,35:06:39.63
19,2020-2021,1775.01,149.23,10:00:27.62,39:27:27.9
20,2020-2021,1776.01,44.65,10:59:06.55,40:59:01.39
21,2020-2021,1779.01,33.93,09:51:04.45,35:58:06.8
22,2020-2021,1789.01,229.07,09:30:58.42,26:32:23.98
23,2020-2021,1797.01,82.34,10:51:06.41,25:38:27.83
24,2020-2021,1799.01,62.13,11:08:55.9,34:18:10.85
25,2020-2021,1800.01,277.28,11:25:05.98,41:01:40.87
26,2020-2021,1801.01,30.68,11:42:18.14,23:01:37.32
27,2020-2021,1802.01,60.69,10:57:01.28,24:52:56.42
28,2020-2021,1803.01,119.24,11:52:11.07,35:10:18.48
29,2020-2021,1806.01,55.52,11:04:28.36,30:27:30.87
30,2020-2021,1821.01,21.56,11:14:33.04,25:42:38.15
31,2020-2021,1822.01,312.52,11:11:06.68,39:31:36.02
32,2020-2021,1898.01,79.67,09:38:13.27,23:32:48.29
33,2022-2023,1683.01,51.19,04:23:55.12,27:49:20.53
34,2022-2023,1685.01,37.62,04:34:22.55,43:02:13.34
35,2022-2023,1693.01,30.79,06:01:14,34:46:23.13
36,2022-2023,1696.01,64.92,04:21:07.36,48:49:11.39
37,2022-2023,1713.01,138.37,06:42:04.94,39:50:34.45
38,2022-2023,1730.01,35.69,07:11:27.8,48:19:40.56
39,2022-2023,3772.01,309.14,05:44:10.44,36:04:50.35
40,2022-2023,3795.01,439.84,06:34:55.79,49:40:35.67
41,2022-2023,3800.01,598.89,06:53:06.26,39:07:56.2
42,2022-2023,4596.01,93.49,06:34:49.88,27:23:16.86
43,2022-2023,4604.01,90.06,05:05:47.03,21:32:53.52
44,2022-2023,4610.01,47.91,05:16:10.38,30:35:06.26
45,2022-2023,5087.01,59.25,04:29:39.09,22:52:57.24
46,2022-2023,5129.01,201.91,06:38:48.67,29:05:21.56
47,2022-2023,1459.01,101.36,01:17:26.83,26:44:45.42
48,2022-2023,1468.01,24.74,01:06:36.93,19:13:29.71
49,2022-2023,1471.01,67.55,02:03:37.2,21:16:52.78
50,2022-2023,4511.01,121.83,03:17:13.27,15:30:06.22
51,2022-2023,4524.01,63.68,03:16:42.75,15:39:22.88
52,2022-2023,4548.01,165.59,02:25:21.87,25:31:50.44
53,2022-2023,4607.01,180.02,01:55:37.25,24:07:05.35
54,2022-2023,4637.01,112.15,02:13:03.56,19:24:09.6
55,2022-2023,4639.01,205.74,01:49:15.49,21:42:12.57
56,2022-2023,4649.01,148.25,01:59:49.57,16:20:48.1
57,2022-2023,5076.01,82.86,03:22:02.5,17:14:21.15
58,2022-2023,5084.01,21.36,03:03:49.09,20:06:38.12
59,2022-2023,5319.01,61.17,02:20:51.25,23:31:13.59
60,2022-2023,5343.01,120.86,03:12:06.25,24:32:00.82
61,2022-2023,5358.01,138.71,03:36:44.14,28:33:00.97
62,2022-2023,5553.01,103.35,02:52:00.52,15:03:20.39
```

The six unique nominal sites within 100 light-years are TOI 488.01, 562.01, 1726.01, 1821.01, 1468.01, and 5084.01. Their distances are approximately 89.2364, 30.7892, 73.0590, 70.3193, 80.6911, and 69.6670 ly, respectively. This conversion was performed during planning; it is a geometry check, not evidence of arrivals.

## Appendix C. Archive integrity and final handoff checks

These are SHA-256 hashes returned by the archive metadata, not hashes of CSV bytes downloaded during planning. Verify them when data are obtained.

| File | Bytes | SHA-256 |
|---|---:|---|
| `GBT20200422.csv` | 1120611827 | `92c035e21f44dd079d793b19b50155458e5fb661af3498f24e42d262a0ff22ec` |
| `GBT20210428.csv` | 1052950134 | `23058a6a79dc7ea50accfd1224e8e599c63dec078db98884e8f880a5c159ab74` |
| `GBT20220522.csv` | 992187571 | `23d6eb53ac8da7cacac315710a26c445870d82613da72c888750b469e24409d4` |
| `GBT20230513.csv` | 1187859985 | `2f10df194e004406c9b9861470724fe115ea466c3a94f351c458d9914f16d1a2` |
| `README.md` | 2665 | `28b528000ad4f48aed8a1b0ee8173df383f4ee366f5aa5ee14a4e6763fc3cb51` |

Before ending your execution, confirm that the report identifies every unperformed validation, contains no invented schedule or calibration truth, reproduces its tables from saved results, includes all unresolved models in outer envelopes, and distinguishes analytic impossibility from finite-simulation non-observation. Verify all artifact paths and commands. Stop optional work once the reached claim is adequately resolved or a gate has conclusively limited it.
