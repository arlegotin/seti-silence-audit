"""Evidence-only scientific tables, scoped conclusions, and exportable figures."""

from dataclasses import asdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import time

from .artifacts import canonical_hash, read_json_checked, write_json_atomic
from .contracts import WeightBounds
from .inference import summarize
from .resources import ResourceLedger, resource_preflight

OUTCOMES = {"supported contribution", "informative negative result", "practical infeasibility",
            "inconclusive evidence", "invalid experiment"}
ROW_FIELDS = ("cell_id", "family_ids", "model_kind", "model_id", "mu", "age_years", "speed_id", "k", "emission_id", "detector_id",
              "visit_dependence", "estimate_status", "weighted_point_bounds", "raw_ideal_likelihood_ratio",
              "schedule_grade", "detector_grade", "C", "likelihood", "R0", "R", "intervals", "numerical_errors",
              "compatibility", "attempted", "surviving", "nulls", "arrivals", "checkpoint_ids", "completion_status",
              "failure_ids", "evidence_ids", "protocol_hash")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _csv(path, fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))
                         if isinstance(value, (dict, list, tuple)) else value for key, value in row.items() if key in fields})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stream.getvalue())


def _load_evidence(root, protocol_path=None):
    lock = read_json_checked(protocol_path or root / "protocol.lock.json")
    body = {k: v for k, v in lock.items() if k != "protocol_hash" and not k.startswith("_")}
    if canonical_hash(body) != lock["protocol_hash"]:
        raise ValueError("Saved protocol hash mismatch")
    matrix = read_json_checked(root / "matrix.json", lock["matrix_sha256"])
    registry = read_json_checked(root / "bound_registry.json", lock["registry_sha256"])
    if matrix["cells"] != lock["cells"] or registry != lock["bound_registry"]:
        raise ValueError("Saved matrix/registry mismatch")
    result = read_json_checked(root / "confirmation.json")
    if (result["protocol_hash"] != lock["protocol_hash"]
            or result.get("content_hash") != canonical_hash({k: v for k, v in result.items() if k != "content_hash"})):
        raise ValueError("Saved result hash mismatch")
    return lock, result


def _report_view(lock, result, oracle_rows):
    raw = {row["cell_id"]: row for row in result["summary"]["rows"]}
    if len(raw) != len(result["summary"]["rows"]) or set(raw) - {c["cell_id"] for c in lock["cells"]}:
        raise ValueError("Duplicate or unregistered result cells")
    cells = []
    valid = {}
    for original in lock["cells"]:
        cell = dict(original)
        row = raw.get(cell["cell_id"])
        usable = row is not None and row.get("completion_status") not in {"pending", "invalid", "missing_numerical_validation"}
        if row is not None and row.get("protocol_hash") != lock["protocol_hash"]:
            raise ValueError("Result row belongs to another protocol")
        if usable and cell["model_kind"] == "independent_sites" and cell["cell_id"] not in oracle_rows:
            usable = False
        if usable:
            bounds = {q: list(row["intervals"][q]) for q in ("C", "likelihood", "R0", "R")}
            for interval in bounds.values():
                WeightBounds(*interval)
            # The saved intervals already include numerical uncertainty.
            cell.pop("numerical_errors", None)
            cell["deterministic"] = bounds | {"status": "validated", "estimates": row.get("estimates", {})}
            valid[cell["cell_id"]] = row
        cells.append(cell)
    # Recompute envelopes from the complete mandatory matrix. A truncated table
    # cannot silently turn an unresolved high-risk model into a positive result.
    summary = summarize({}, dict(lock, cells=cells), {})
    return summary, valid, raw


def _rows(lock, result, summary, valid, raw, oracle_rows):
    rows = []
    lookup = {c["cell_id"]: c for c in lock["cells"]}
    totals = result.get("execution_totals", {}).get("groups", {})
    demographics = {m["model_id"]: m for m in lock.get("config", {}).get("models", ())}
    for row in summary.rows:
        cid = row["cell_id"]
        original, saved = lookup[cid], valid.get(cid)
        counts = saved.get("counts") if saved else None
        kind, mid = row["model_kind"], row["model_id"]
        group = f"{'ideal' if kind == 'ideal_silence' else kind}:{mid}"
        nulls = None
        if counts and not original.get("analytic_unconstrained_detector"):
            bounds = counts.get("bound_counts", {})
            nulls = {"low": bounds["null_low"], "high": bounds["null_high"]} if bounds else counts["nulls"]
        error = saved.get("numerical_errors", {}) if saved else {}
        if cid in oracle_rows:
            error = oracle_rows[cid].get("numerical_errors", error)
        exported = {"cell_id": cid, "family_ids": row.get("families", []), "model_kind": kind,
                    "model_id": mid, "k": row["future_multiplier"], "emission_id": row.get("emission_id"),
                    **{key: demographics.get(mid, {}).get(key) for key in ("mu", "age_years", "speed_id")},
                    "detector_id": row.get("detector_id"), "schedule_grade": row.get("schedule_grade"),
                    "visit_dependence": original.get("visit_dependence", "nominal"),
                    "estimate_status": saved.get("estimate_status", {}) if saved else {q: "unavailable" for q in ("C", "likelihood", "R0", "R")},
                    "weighted_point_bounds": saved.get("weighted_point_bounds") if saved else None,
                    "raw_ideal_likelihood_ratio": saved.get("raw_ideal_likelihood_ratio") if saved else None,
                    "detector_grade": row.get("detector_grade"), **row["estimates"],
                    "intervals": row["intervals"], "numerical_errors": error,
                    "compatibility": row["compatibility"], "attempted": totals.get(group, {}).get("attempted_proposals"),
                    "surviving": counts["histories"] if counts else None, "nulls": nulls,
                    "arrivals": counts["arrivals"] if counts else None,
                    "checkpoint_ids": sorted(set(original.get("interval_ids", {}).values()) |
                                              ({original["survival_interval_id"]} if "survival_interval_id" in original else set())),
                    "completion_status": saved["completion_status"] if saved else "pending",
                    "failure_ids": [] if saved else [f"missing_or_invalid:{cid}"],
                    "evidence_ids": ["protocol", "confirmation"], "protocol_hash": lock["protocol_hash"]}
        if kind == "independent_sites" and saved:
            exported["evidence_ids"].append("independent_oracles")
        rows.append(exported)
    return rows


def _claims(lock, result, summary, rows, theorem, extra):
    claims = []
    pending = [r["cell_id"] for r in rows if r["completion_status"] == "pending"]
    for family, decisions in summary.certificates.items():
        decision = decisions["0.05"]
        if decision == "material":
            category = "supported contribution"
            statement = "The upper arrival-risk envelope materially narrows under this declared observation model."
        elif decision in {"nonmaterial", "incompatible"}:
            category = "informative negative result"
            statement = ("Material upper-envelope narrowing is ruled out in this family." if decision == "nonmaterial"
                         else "The evaluated family is excluded by the declared null-compatibility convention; no conditional family risk is assigned.")
        else:
            category = None
            statement = "The supplied certified enclosures do not resolve this family's material-narrowing question."
        unresolved = [r["cell_id"] for r in rows if r["cell_id"] in pending and family in r["family_ids"]]
        claims.append({"claim_id": "family:" + family, "claim": statement, "decision": decision,
                       "outcome_category": category, "status": "resolved" if category else "analysis_pending",
                       "scope": family + "; tau=.05; conditional model calculation; " + lock["purpose"],
                       "threshold_decisions": decisions, "evidence_ids": ["protocol", "confirmation"],
                       "unresolved_dependencies": unresolved or (["Resolve statistical or nuisance-bound ambiguity; do not interpret it as a negative."] if category is None else [])})
    grade = lock["schedule"]["detector_grade"]
    timing = lock["schedule"]["schedule_grade"]
    missing = []
    if timing != "exact":
        missing.append("complete source-backed observing log")
    if grade != "calibrated":
        missing.append("evidence-backed final-selection calibration bridge")
    claims.append({"claim_id": "survey_calibrated_inference", "claim": "A telescope-calibrated numerical arrival constraint requires the missing empirical prerequisites.",
                   "outcome_category": "inconclusive evidence" if missing else None,
                   "scope": f"{timing}; {grade}; {lock['purpose']}", "evidence_ids": ["protocol"],
                   "unresolved_dependencies": missing})
    reference_status = theorem.get("status", "unperformed")
    category = ("invalid experiment" if reference_status == "failed" else
                "supported contribution" if reference_status == "validated" and all(r.get("consistent") for r in result.get("reference_checks", ()))
                and result.get("reference_checks") else None)
    claims.append({"claim_id": "continuum_reference", "claim": "Independent finite-age formula and shell consistency checks are separate from the stellar survey inference.",
                   "outcome_category": category, "scope": "continuum reference; " + lock["purpose"],
                   "evidence_ids": ["theorem"] if theorem else ["protocol"],
                   "unresolved_dependencies": [] if category else ["Complete or supply the reference checks and their uncertainty evidence."]})
    known = {c["claim_id"] for c in claims}
    for claim in extra:
        if claim["claim_id"] in known or claim.get("outcome_category") not in OUTCOMES | {None}:
            raise ValueError("Duplicate claim or unsupported outcome category")
        if claim.get("outcome_category") == "practical infeasibility":
            basis = claim.get("basis", {})
            if not basis.get("attempted_remedies") or not (basis.get("measured_requirement_bytes", 0) > basis.get("available_bytes", 0)):
                raise ValueError("Practical infeasibility requires measured capacity and attempted remedies")
        known.add(claim["claim_id"])
        claims.append(claim)
    return sorted(claims, key=lambda c: c["claim_id"])


def _comparison_rows(rows):
    lookup = {(r["model_kind"], r["model_id"], r["k"], r["emission_id"], r["detector_id"], r["visit_dependence"]): r for r in rows}
    comparisons = []
    for row in rows:
        if row["model_kind"] != "interacting":
            continue
        for label, other_key in (("interaction_minus_independent", ("independent_sites", row["model_id"], row["k"], row["emission_id"], row["detector_id"], row["visit_dependence"])),
                                 ("survey_minus_ideal", ("ideal_silence", row["model_id"], row["k"], "E1", "perfect", "nominal"))):
            if label == "survey_minus_ideal" and (row["emission_id"], row["detector_id"]) != ("E1", "Dnom"):
                continue
            other = lookup.get(other_key)
            if other:
                a, b = row["intervals"]["R"], other["intervals"]["R"]
                comparisons.append({"comparison": label, "cell_id": row["cell_id"], "other_cell_id": other["cell_id"],
                                    "model_id": row["model_id"], "k": row["k"], "difference_low": a[0] - b[1],
                                    "difference_high": a[1] - b[0], "scope": "observation-model sensitivity" if label == "survey_minus_ideal" else "matched suppression sensitivity"})
    return comparisons


def _figures(output, root, lock, summary, rows, comparisons, theorem):
    slots = {key: {"status": "table_substitute", "reason": "Too few independently resolved model rows for a useful plot."}
             for key in ("family_envelopes", "likelihood_risk", "ideal_discrepancy", "theorem_ratios")}
    candidates = [r for r in rows if "interacting/primary" in r["family_ids"] and r["completion_status"] != "pending"]
    paths = {}
    if len(candidates) >= 3 or theorem.get("status") == "validated":
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        directory = output / "figures"; directory.mkdir(parents=True, exist_ok=True)
        def save(fig, name):
            fig.text(.01, .01, "Protocol " + lock["protocol_hash"][:12] + "; " + lock["purpose"], fontsize=7)
            fig.tight_layout(rect=(0, .04, 1, 1))
            path = directory / (name + ".png")
            fig.savefig(path, dpi=180, metadata={"Software": "seti_audit"})
            plt.close(fig)
            paths[name] = path
            slots[name] = {"status": "generated", "path": str(path.resolve())}
        if len(candidates) >= 3:
            family_names = [name for name in summary.envelopes if name == "interacting/primary" or
                            (name.startswith("interacting/E") and name.endswith("/k1") and "/Duncal" not in name)]
            fig, ax = plt.subplots(figsize=(9, max(3.5, .35 * len(family_names))))
            for i, name in enumerate(family_names):
                entry = summary.envelopes[name]["0.05"]
                for offset, q, color in ((-.08, "I0", "#334e68"), (.08, "Ipost", "#b65c27")):
                    bounds = entry[q]
                    if bounds is not None:
                        ax.plot(bounds, [i + offset, i + offset], color=color, lw=3)
            ax.set_yticks(range(len(family_names)), [name.removeprefix("interacting/") for name in family_names])
            ax.set(xlabel="Century arrival probability: original (blue), null-conditioned outer envelope (orange)", xlim=(0, 1), title="Conditional family ranges; tau=.05")
            save(fig, "family_envelopes")
            fig, ax = plt.subplots(figsize=(7, 4.5))
            for row in candidates:
                x, y = row["intervals"]["likelihood"], row["intervals"]["R"]
                ax.errorbar([(x[0] + x[1]) / 2], [(y[0] + y[1]) / 2],
                            xerr=[[(x[1] - x[0]) / 2]], yerr=[[(y[1] - y[0]) / 2]], fmt="o", ms=3, color="#334e68", alpha=.8)
            for threshold in lock["thresholds"]:
                ax.axvline(threshold, color="#b65c27", ls="--", lw=.8)
            ax.set(xlabel="Null likelihood enclosure", ylabel="Arrival-risk enclosure", title="E1 / Dnom: interval centers with enclosure widths", xlim=(0, 1), ylim=(0, 1))
            save(fig, "likelihood_risk")
        ideal = [r for r in comparisons if r["comparison"] == "survey_minus_ideal" and r["k"] == 1]
        if len(ideal) >= 3:
            fig, ax = plt.subplots(figsize=(8, 4))
            for i, value in enumerate(ideal):
                ax.plot([i, i], [value["difference_low"], value["difference_high"]], color="#334e68", lw=3)
            ax.axhline(0, color="gray", lw=.8)
            ax.set_xticks(range(len(ideal)), [str(r["model_id"]) for r in ideal])
            ax.set(xlabel="Demographic model ID", ylabel="Survey risk minus perfect-silence risk", title="Observation-model sensitivity; both conditioned on their own data")
            save(fig, "ideal_discrepancy")
        if theorem.get("status") == "validated" and theorem.get("ratios"):
            fig, ax = plt.subplots(figsize=(7, 4.5))
            for alpha in sorted({r["alpha"] for r in theorem["ratios"]}):
                curve = sorted([r for r in theorem["ratios"] if r["alpha"] == alpha], key=lambda r: r["h"])
                ax.plot([r["h"] for r in curve], [r["ratio"] for r in curve], marker="o", ms=3, label=f"alpha={alpha:g}")
            ax.axhline(1, color="gray", lw=.8); ax.set_xscale("log"); ax.legend(fontsize=8)
            ax.set(xlabel="Continuum horizon h (T=1)", ylabel="Exact / asymptotic leading mean", title="Finite-age reference; alpha=3 converges logarithmically")
            save(fig, "theorem_ratios")
    for name, slot in slots.items():
        if slot["status"] != "generated":
            slot["table"] = str((root / "tables" / ("theorem_ratios.csv" if name == "theorem_ratios" else "comparisons.csv" if name == "ideal_discrepancy" else "family_envelopes.csv" if name == "family_envelopes" else "model_rows.csv")).resolve())
            if name == "theorem_ratios" and theorem.get("status") != "validated":
                slot.update(status="unperformed", reason="A validated saved continuum-reference artifact is unavailable.")
    return slots, paths


def render_report(results_dir: Path, output_dir: Path, *, protocol_path: Path | None = None) -> dict:
    root, output = Path(results_dir), Path(output_dir)
    protocol_file = Path(protocol_path) if protocol_path is not None else root / "protocol.lock.json"
    if protocol_path is None and not protocol_file.exists():
        return render_evidence_report(root, output)
    lock, result = _load_evidence(root, protocol_file)
    preflight = resource_preflight(output)
    ledger = ResourceLedger(root / "resources.jsonl")
    job, start = ledger.start("G6"), time.perf_counter()
    try:
        output.mkdir(parents=True, exist_ok=True)
        write_json_atomic(root / "report_preflight.json", preflight)
        oracle_rows = {}
        if (root / "independent_oracles.json").exists():
            cached = read_json_checked(root / "independent_oracles.json")
            if cached["protocol_hash"] != lock["protocol_hash"] or cached["content_hash"] != canonical_hash(cached["rows"]):
                raise ValueError("Saved quadrature evidence hash mismatch")
            oracle_rows = cached["rows"]
        theorem = read_json_checked(root / "theorem/deterministic.json") if (root / "theorem/deterministic.json").exists() else {}
        summary, valid, raw = _report_view(lock, result, oracle_rows)
        rows = _rows(lock, result, summary, valid, raw, oracle_rows)
        extra = read_json_checked(root / "claims.json").get("claims", []) if (root / "claims.json").exists() else []
        claims = _claims(lock, result, summary, rows, theorem, extra)
        inputs = {"protocol": protocol_file, "confirmation": root / "confirmation.json",
                  "matrix": root / "matrix.json", "interval_registry": root / "bound_registry.json"}
        for name, path in (("theorem", root / "theorem/deterministic.json"), ("independent_oracles", root / "independent_oracles.json"),
                           ("custom_claims", root / "claims.json"), ("environment", root / "environment.json"),
                           ("pilot", root / "pilot.json"), ("calibration", root / "calibration.json"),
                           ("analytic_controls", root / "analytic_controls.json"), ("correctness", root / "correctness.json")):
            if path.exists():
                inputs[name] = path
        evidence = {name: {"path": str(path.resolve()), "sha256": _sha(path)} for name, path in inputs.items()}
        for claim in claims:
            if not claim.get("evidence_ids") or any(eid not in evidence for eid in claim["evidence_ids"]):
                raise ValueError("Claim refers to missing evidence")
        write_json_atomic(root / "evidence.json", {"evidence": evidence})
        write_json_atomic(root / "model_rows.json", {"protocol_hash": lock["protocol_hash"], "rows": rows})
        write_json_atomic(root / "family_envelopes.json", {"protocol_hash": lock["protocol_hash"], "envelopes": summary.envelopes,
                                                          "certified": summary.certified, "possible": summary.possible, "certificates": summary.certificates})
        write_json_atomic(root / "conclusions.json", {"protocol_hash": lock["protocol_hash"], "purpose": lock["purpose"], "claims": claims})
        _csv(root / "tables/model_rows.csv", ROW_FIELDS, rows)
        _csv(root / "tables/demographics.csv", ("model_id", "mu", "age_years", "speed_id", "future_multiplier"), lock.get("config", {}).get("models", []))
        families = [{"family": family, "threshold": tau, **entry, "decision": summary.certificates[family][tau]}
                    for family, thresholds in summary.envelopes.items() for tau, entry in thresholds.items()]
        _csv(root / "tables/family_envelopes.csv", ("family", "threshold", "I0", "Iselect", "Ipost", "certified_post", "baseline_upper", "post_upper", "decision"), families)
        comparisons = _comparison_rows(rows)
        _csv(root / "tables/comparisons.csv", ("comparison", "cell_id", "other_cell_id", "model_id", "k", "difference_low", "difference_high", "scope"), comparisons)
        _csv(root / "tables/theorem_ratios.csv", ("alpha", "h", "exact", "leading", "ratio"), theorem.get("ratios", []))
        references = [{"h": r["h"], "trials": r["trials"], "contact_count": r["contact_count"],
                       "contact_interval": r["contact_probability_interval"], "rigorous_bounds": r["rigorous_probability_bounds"],
                       "consistent": r["consistent"]} for r in result.get("reference_checks", ())]
        _csv(root / "tables/reference_checks.csv", ("h", "trials", "contact_count", "contact_interval", "rigorous_bounds", "consistent"), references)
        figures, figure_paths = _figures(output, root, lock, summary, rows, comparisons, theorem)
        def link(path):
            relative = os.path.relpath(path, output)
            return "<" + relative + ">" if " " in relative else relative
        primary = next((c for c in claims if c["claim_id"] == "family:interacting/primary"), None)
        lead = primary["claim"] if primary else "The saved evidence contains no completed primary-family decision."
        synthetic = lock["purpose"] != "research"
        primary_envelope = summary.envelopes.get("interacting/primary", {}).get("0.05")
        numerical_lead = (f"Primary upper-envelope enclosures: before the null {primary_envelope['baseline_upper']}; "
                          f"after the null {primary_envelope['post_upper']}. "
                          f"Certified retained models: {len(summary.certified['interacting/primary']['0.05'])}; "
                          f"possibly retained: {len(summary.possible['interacting/primary']['0.05'])}."
                          if primary_envelope else "Primary comparison not supplied.")
        provenance = lock.get("catalog_provenance", {})
        catalog_summary = {key: provenance.get(key) for key in ("source_status", "source_rows", "physical_sites", "duplicate_sites")}
        environment = read_json_checked(root / "environment.json") if (root / "environment.json").exists() else {}
        environment_summary = {key: environment.get(key) for key in ("architecture", "python_version", "physical_memory_bytes", "cpu_available", "precision", "packages")}
        lines = ["# SETI silence audit", "", ("**Synthetic offline control. No survey research conclusion is claimed.**" if synthetic else lead), "",
                 f"Evidence grade: `{lock['schedule']['schedule_grade']}` / `{lock['schedule']['detector_grade']}`. Protocol `{lock['protocol_hash']}`.", "",
                 numerical_lead, "",
                 "This audit concerns physical arrival within 100 Julian years after the survey endpoint. Radio reception is a different event. Every modeled risk stipulates that Earth has not already been reached; a small survival probability C does not penalize a model.", "",
                 "## Scope and assumptions", "", f"Saved endpoint: `{json.dumps(lock['schedule'].get('endpoint', {}), sort_keys=True)}`.", "",
                 f"Catalog summary: `{json.dumps(catalog_summary, sort_keys=True)}`. Full source/configuration provenance is retained in the frozen protocol.", "",
                 "The research catalog has 62 published rows and 61 physical sites: TOI 1730.01 has two visits but one birthplace. The synthetic controls use their own explicitly declared geometry.", "",
                 "Measured survey information and source verification are distinct from assumed birth rates, historical age, expansion speeds, emission behavior, detector transfer, and future continuation. F1 preserves permitted observation intervals; F2 point-detector efficiencies remain assumptions. Zero-response Duncal and invisible counterparts prevent full-family contraction; a displayed outer [0,1] is not a claim that both endpoints are achievable.", "",
                 "The primary research family models only the catalog sites, equal potential-birth hazards, a 10,000-year start, mu in {.1,1,3,12}, and four declared speed laws. It is not a Galactic forecast. E1 assumes compatible, immediate, persistent emission; E2 has .1 compatibility, E3 delays emission 100 years, E4 has a 100-year radio life, and E5 has stationary .1 ON fraction with one-day correlation. E0 is invisible.", "",
                 "Dnom assumes .8836 final-pair recovery, Dweak .44, Dhigh .94, and Dpositive the full [.44,.94] interval. Duncal admits zero response. Numerical confidence refers to calculation under these assumptions, not to their astrophysical truth. Archive timing precision does not establish equal astrophysical precision.", "",
                 "The scientific comparisons are one-factor sensitivities. Future k=0/10 controls cover E1/E0, not every emission cross-combination. Age diagnostics hold mu fixed, not the present birth rate.", "",
                 "F1 already relaxes repeated-visit dependence, so its nominal and dependence-robust scenarios share the same enclosure. Dpositive's .44 lower response is an assumption, not an empirical calibration bound.", "",
                 "## Decisions and uncertainty", "", "C is survival probability, likelihood is null probability conditional on survival, R0 is century-arrival risk before the radio null, and R is risk after the null. Weighted point estimates and certified intervals are separate. A null can increase a risk.", "",
                 "Compatibility retains likelihood >= tau; equality is retained. An entirely excluded family has no conditional family risk. Missing or invalid cells remain in the outer envelope. Material narrowing requires both absolute .01 and relative .25 upper-envelope contraction; a negative uses its own conservative certificate.", "",
                 "One independent history is the independent unit. Stars, visits, and paired variants are not extra replicates. Exact binomial audit intervals use the frozen registry and alpha=A/(M*j*(j+1)); thresholds reuse those intervals. Calibration/astrophysical uncertainty is separate from Monte Carlo confidence.", "",
                 f"[Per-model table]({link(root / 'tables/model_rows.csv')}); [all family envelopes]({link(root / 'tables/family_envelopes.csv')}); [scoped conclusions]({link(root / 'conclusions.json')}).", "",
                 f"[Demographic definitions]({link(root / 'tables/demographics.csv')}). Raw ideal-silence likelihood ratios are retained when noisy survival normalization makes the point exceed one; the displayed point is clipped and its conservative interval is unchanged.", "",
                 "## Interaction and observation sensitivity", "", f"[Matched interaction and ideal-silence differences]({link(root / 'tables/comparisons.csv')}). Differences retain their signs. Perfect simultaneous silence is an observation-model sensitivity, not a competitor using the same telescope data.", "",
                 "## Continuum reference", "", f"Saved deterministic status: `{theorem.get('status', 'unperformed')}`. The warning display on PDF page 8 is damaged; the implemented warning formula is an independent repair from E8. Original source scripts were not supplied or reproduced. Continuum asymptotics are not imported as exponents for the finite stellar catalog.", "",
                 f"[Exact/leading reference table]({link(root / 'tables/theorem_ratios.csv')}); [finite-shell trial counts and rigorous bounds]({link(root / 'tables/reference_checks.csv')}).", "",
                 "## Costs, failures, and missing work", "", f"Resource totals recorded before this rendering: `{json.dumps(ledger.usage(), sort_keys=True)}`. These sum recorded job durations, including nested checks; they are not unique elapsed wall time. The append-only resource ledger also records this rendering after it finishes.", "",
                 f"Saved scientific environment: `{json.dumps(environment_summary, sort_keys=True)}`. Current report preflight: `{json.dumps(preflight, sort_keys=True)}`.", "",
                 "Runtime estimates and sample checkpoints impose no deadline, launch allowance, byte quota, or maximum precision look. Actual capacity interruptions preserve resumable work. An interruption is not a scientific outcome.", "",
                 f"Unperformed or invalid required result rows: `{json.dumps([r['cell_id'] for r in rows if r['completion_status'] == 'pending'])}`.", "",
                 "## Artifacts", ""]
        for name, slot in figures.items():
            if slot["status"] == "generated":
                lines.extend([f"![{name.replace('_', ' ')}]({link(Path(slot['path']))})", ""])
            else:
                lines.extend([f"{name.replace('_', ' ')}: {slot['reason']} [Saved table]({link(Path(slot['table']))}).", ""])
        lines.extend([f"[Evidence paths and hashes]({link(root / 'evidence.json')}). Report regeneration reads saved evidence and performs no acquisition or simulation.", "",
                      "One next empirical step is to obtain the complete observing and final-selection calibration package. Conditional numerical findings remain scoped to their declared model family.", ""])
        (output / "REPORT.md").write_text("\n".join(lines))
        outputs = {"report": output / "REPORT.md", "conclusions": root / "conclusions.json", "model_rows": root / "model_rows.json",
                   "family_envelopes": root / "family_envelopes.json", "evidence": root / "evidence.json",
                   "model_table": root / "tables/model_rows.csv", "family_table": root / "tables/family_envelopes.csv",
                   "comparisons": root / "tables/comparisons.csv", "theorem_table": root / "tables/theorem_ratios.csv"}
        outputs.update(demographics=root / "tables/demographics.csv", reference_checks=root / "tables/reference_checks.csv")
        outputs.update({"figure_" + name: path for name, path in figure_paths.items()})
        manifest = {"protocol_hash": lock["protocol_hash"], "figures": figures,
                    "artifacts": {name: {"path": str(path.resolve()), "sha256": _sha(path)} for name, path in outputs.items()}}
        write_json_atomic(output / "manifest.json", manifest)
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, 0, status="failed", details={"exception": type(exc).__name__})
        raise
    ledger.finish(job, time.perf_counter() - start, 0, details={"artifact": str(output / "REPORT.md"), "rows": len(rows)})
    return manifest


def render_evidence_report(results_dir: Path, output_dir: Path, *, evidence_path: Path | None = None) -> dict:
    """Report independently resolved/blocked components without a fake lock."""
    root, output = Path(results_dir), Path(output_dir)
    status = read_json_checked(evidence_path or root / "evidence_status.json")
    if status.get("stage") != "pre_freeze":
        raise ValueError("Unfrozen evidence report requires explicit pre_freeze status")
    resource_preflight(output)
    evidence = {}
    for identifier, item in status["evidence"].items():
        path = Path(item["path"])
        if not path.is_absolute():
            path = root / path
        if _sha(path) != item["sha256"]:
            raise ValueError("Unfrozen evidence hash mismatch")
        evidence[identifier] = {"path": str(path.resolve()), "sha256": item["sha256"]}
    claims = status["claims"]
    for claim in claims:
        if (claim.get("outcome_category") not in OUTCOMES | {None} or not claim.get("evidence_ids")
                or any(identifier not in evidence for identifier in claim["evidence_ids"])):
            raise ValueError("Unfrozen claim lacks valid scoped evidence")
    output.mkdir(parents=True, exist_ok=True)
    ledger = ResourceLedger(root / "resources.jsonl")
    job, start = ledger.start("G6"), time.perf_counter()
    try:
        write_json_atomic(root / "evidence.json", {"evidence": evidence})
        write_json_atomic(root / "conclusions.json", {"protocol_hash": None, "purpose": status["purpose"], "claims": claims})
        write_json_atomic(root / "model_rows.json", {"protocol_hash": None, "rows": []})
        _csv(root / "tables/model_rows.csv", ROW_FIELDS, [])
        text = ["# SETI component evidence", "", "The experiment is not frozen. No numerical confirmation is claimed.", "",
                "Synthetic control." if status["purpose"] != "research" else "Research component evidence.", "",
                f"Schedule grade: {status.get('schedule_grade', 'unavailable')}. Detector grade: {status.get('detector_grade', 'unavailable')}.", ""]
        for claim in claims:
            text.extend([f"{claim['claim_id']}: {claim['claim']} Scope: {claim['scope']}. Outcome: {claim.get('outcome_category') or 'pending'}.",
                         f"Unresolved prerequisites: {json.dumps(claim.get('unresolved_dependencies', []))}.", ""])
        text.append("All unaffected research and required validation remain pending unless independently resolved by the listed evidence.")
        (output / "REPORT.md").write_text("\n".join(text) + "\n")
        outputs = {"report": output / "REPORT.md", "conclusions": root / "conclusions.json", "model_rows": root / "model_rows.json",
                   "evidence": root / "evidence.json", "model_table": root / "tables/model_rows.csv"}
        manifest = {"protocol_hash": None, "figures": {name: {"status": "unperformed", "reason": "Experiment not frozen"}
                                                       for name in ("family_envelopes", "likelihood_risk", "ideal_discrepancy", "theorem_ratios")},
                    "artifacts": {name: {"path": str(path.resolve()), "sha256": _sha(path)} for name, path in outputs.items()}}
        write_json_atomic(output / "manifest.json", manifest)
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, 0, status="failed", details={"exception": type(exc).__name__})
        raise
    ledger.finish(job, time.perf_counter() - start, 0, details={"scope": "pre_freeze_evidence"})
    return manifest


def run_smoke(protocol, output_dir: Path, ledger: ResourceLedger) -> dict:
    """One seeded synthetic stellar history, with linked visits and real I/O.

    The same tiny protocol also exercises the separately identified ideal and
    continuum reference paths. None of its results is survey evidence.
    """
    from dataclasses import replace
    import numpy as np
    from .contracts import (CalibrationResult, Catalog, Geometry, ModelConfig, PilotResult, Scan, Schedule)
    from .experiments import freeze_protocol, run_confirmation
    from .data import ON_DURATION_YEARS
    output = Path(output_dir)
    root = output / "results"
    tiny = replace(protocol, purpose="smoke", models=(ModelConfig(0, 5, 10, "S1"),), source_hashes={},
                   initial_checkpoints={key: 1 for key in protocol.initial_checkpoints})
    geometry = Geometry(("synthetic-star",), np.array([[1., 0, 0]]), np.array([1.]), np.zeros((1, 1)))
    provenance = {"source_status": "synthetic_control", "physical_sites": 1, "source_rows": 2,
                  "scope": "one seeded single-star history; two linked synthetic visits"}
    catalog = Catalog(({"source_row": "synthetic-1"}, {"source_row": "synthetic-2"}), geometry, provenance)
    scans = tuple(Scan(f"synthetic-{visit}", "synthetic-star", index + 1, start, ON_DURATION_YEARS, "synthetic-OFF")
                  for visit, starts in enumerate(((-.5, -.4), (-.2, -.1))) for index, start in enumerate(starts))
    schedule = Schedule(scans, (), "exact", "assumed_F2", {"t0": "synthetic_zero"}, provenance)
    calibration = CalibrationResult({0: 1}, {}, 1, 0., {0: 0.}, {0: WeightBounds(1., 1.)},
                                    {"scope": "synthetic smoke only"}, 0, (), ("synthetic-smoke",))
    pilot = PilotResult(True, ("synthetic-smoke",), {"scope": "synthetic smoke only"}, {})
    start, job = time.perf_counter(), ledger.start("smoke")
    try:
        lock = freeze_protocol(tiny, catalog, schedule, calibration, pilot, root)
        result = run_confirmation(lock, (root / "confirmation.json").exists(), ledger)
        manifest = render_report(root, output / "report")
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, 0, status="failed", details={"exception": type(exc).__name__})
        raise
    ledger.finish(job, time.perf_counter() - start, 0, details={"purpose": "synthetic smoke", "protocol_hash": lock["protocol_hash"]})
    return {"status": result["status"], "purpose": "synthetic smoke", "protocol_hash": lock["protocol_hash"],
            "report": manifest["artifacts"]["report"], "elapsed_seconds": time.perf_counter() - start}
