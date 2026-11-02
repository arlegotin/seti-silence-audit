"""Seed-stable, checkpoint-extensible research execution with durable batches."""

from contextlib import contextmanager
from dataclasses import asdict, replace
import fcntl
import math
from pathlib import Path
import time

import numpy as np

from .artifacts import canonical_hash, read_json_checked, write_json_atomic
from .contracts import (AuditCounts, BoundedVisit, ClockBatch, DetectorConfig,
                        EmissionConfig, Geometry, Scan, Schedule, WeightBounds, parse_protocol)
from .detection import batch_null_weights
from .experiments import paired_future_batches, verify_protocol_lock
from .inference import (accumulate, accumulate_bounds, alpha_at_checkpoint,
                        certify_narrowing, exact_interval, summarize)
from .model import _uniform_open, sample_clock_batch, simulate_batch
from .oracles import independent_oracle
from .storage import commit_batch, load_committed_batches


@contextmanager
def _run_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "run.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _objects(lock):
    protocol = parse_protocol(lock["config"])
    geometry = Geometry(**lock["geometry"])
    raw = lock["schedule"]
    schedule = Schedule(tuple(Scan(**s) for s in raw["exact_scans"]),
                        tuple(BoundedVisit(**v) for v in raw["bounded_visits"]), raw["schedule_grade"],
                        raw["detector_grade"], raw["endpoint"], raw["provenance"])
    return protocol, geometry, schedule


def _groups(lock):
    groups = {}
    for model in lock["config"]["models"]:
        mid = model["model_id"]
        groups[f"interacting:{mid}"] = {"kind": "interacting", "model_id": mid, "initial": lock["initial_survivors"][str(mid)]}
        if mid < 16:
            groups[f"ideal:{mid}"] = {"kind": "ideal", "model_id": mid, "initial": lock["initial_ideal_survivors"]}
        if str(mid) in lock["initial_diagnostic_proposals"]:
            groups[f"diagnostic:{mid}"] = {"kind": "diagnostic", "model_id": mid, "initial": lock["initial_diagnostic_proposals"][str(mid)]}
    for index in (0, 1):
        groups[f"shell:{index}"] = {"kind": "shell", "model_id": index,
                                     "initial": lock["config"]["initial_checkpoints"]["shell_histories"]}
    return groups


def _rng(kind, model_id, purpose, batch_index, phase=1):
    stage = {"interacting": 4, "diagnostic": 5, "ideal": 6, "shell": 7}[kind]
    seed = [20261101, phase, stage, model_id, purpose, batch_index]
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed))), seed


def _merge(parts):
    first = parts[0]
    if any(set(p.bound_counts) != set(first.bound_counts) for p in parts):
        raise ValueError("Inconsistent bound components across batches")
    return AuditCounts(*(sum(getattr(p, key) for p in parts) for key in ("histories", "arrivals", "nulls", "arrival_nulls")),
                       math.fsum(p.sum_w for p in parts), math.fsum(p.sum_bw for p in parts),
                       {q: sum(p.bound_counts[q] for p in parts) for q in first.bound_counts},
                       {q: math.fsum(p.bound_sums[q] for p in parts) for q in first.bound_sums})


def _all_counts(batches):
    parts = {}
    for batch in batches:
        for cell_id, value in batch["counts_by_cell"].items():
            parts.setdefault(cell_id, []).append(AuditCounts(**value))
    return {key: _merge(values) for key, values in parts.items()}


def _compute_batch(lock, group, index, count, look, objects, ledger):
    protocol, geometry, schedule = objects
    kind, mid = group["kind"], group["model_id"]
    model = next((m for m in protocol.models if m.model_id == mid), None) if kind != "shell" else None
    start = time.perf_counter()
    job = ledger.start("G4" if kind == "interacting" else "G5", ensemble_id=mid,
                       details={"protocol_hash": lock["protocol_hash"], "group_id": f"{kind}:{mid}", "batch_index": index})
    work, attempts, counts, roots, states, extra = 0, 0, {}, {}, {}, {}
    numerical = {"open_uniform_rejections": 0, "speed_rounding_count": 0, "speed_rounding_mass_bound": 0.,
                 "history_scalar_rechecks": 0, "source_precision_rechecks": 0}
    boundary_rechecks = []
    def note_clock(diagnostics):
        for key in ("open_uniform_rejections", "speed_rounding_count", "speed_rounding_mass_bound"):
            numerical[key] += diagnostics.get(key, 0)
    def note_history(history, context):
        nonlocal work
        checks = history.diagnostics.get("scalar_rechecks", {})
        numerical["history_scalar_rechecks"] += len(checks)
        work += len(checks)
        boundary_rechecks.extend({"context": context, "history_index": int(i), "diagnostics": value}
                                 for i, value in checks.items())
    purpose = {"diagnostic": 40, "ideal": 50, "interacting": 10, "shell": 70}[kind]
    phase = lock["rng"]["root"][1]
    prefix_rng, roots["prefix"] = _rng(kind, mid, purpose, index, phase)
    try:
        if kind == "shell":
            from .theorem import sample_shell, shell_evidence
            h = (.02, .5)[mid]
            sample = sample_shell({"alpha": 1, "h": h, "phase": "confirmation", "protocol_hash": lock["protocol_hash"]},
                                  prefix_rng, count, ledger)
            # sample_shell owns the resource record for its actual histories;
            # this outer publication job must not charge them a second time.
            attempts = count
            counts[f"shell:{mid}:contact"] = AuditCounts(count, sample.contact_count, 0, 0, 0., 0., {})
            for z in (.25, .5, .75, 1.):
                for u in (.25, .5, .75, 1.):
                    successes = int(np.sum((sample.free_horizon_fractions <= z) & (sample.free_warning_fractions <= u)))
                    counts[f"shell:{mid}:z{z:g}:u{u:g}"] = AuditCounts(count, successes, 0, 0, 0., 0., {})
            extra["shell_summary"] = shell_evidence(sample, h)
            extra["nested_history_evaluations"] = sample.trials
        elif kind == "diagnostic":
            clocks = sample_clock_batch(model, geometry, prefix_rng, count, "lower_cone", 0)
            note_clock(clocks.diagnostics)
            history = simulate_batch(clocks, geometry)
            work += count; attempts += count
            note_history(history, "proposal_diagnostic")
            counts[f"proposal:{mid}"] = AuditCounts(count, int(np.sum(history.survives)), 0, 0, 0., 0., {})
        else:
            if kind == "ideal":
                prefix = sample_clock_batch(model, geometry, prefix_rng, count, "ideal_silence", 0)
                attempts += count
                note_clock(prefix.diagnostics)
            else:
                remaining, birth_parts, speed_parts, gap_parts = count, [], [], []
                while remaining:
                    proposed = sample_clock_batch(model, geometry, prefix_rng, remaining, "lower_cone", 0)
                    note_clock(proposed.diagnostics)
                    histories = simulate_batch(proposed, geometry)
                    attempts += remaining; work += remaining
                    note_history(histories, f"prefix_attempts_through_{attempts}")
                    keep = histories.survives
                    if model.speed_id in ("S1", "S2") and not np.all(keep):
                        raise ArithmeticError("Common-speed proposal violated exact survival")
                    birth_parts.append(proposed.birth_years[keep]); speed_parts.append(proposed.speeds[keep]); gap_parts.append(proposed.speed_gaps[keep])
                    remaining -= int(np.sum(keep))
                    ledger.progress(job, time.perf_counter() - start, work,
                                    details={"group": kind, "model_id": mid, "survivors_pending": remaining, "attempts": attempts})
                prefix = ClockBatch(np.concatenate(birth_parts), np.concatenate(speed_parts), np.concatenate(gap_parts))
            future_rng, roots["future"] = _rng(kind, mid, 20, index, phase)
            multipliers = (0., 1., 10.) if mid < 16 else (1.,)
            futures = paired_future_batches(prefix, model, geometry, future_rng, multipliers)
            work += count * len(multipliers)
            note_clock(futures[1.].diagnostics.get("batch_clock_diagnostics", {}).get("mark_diagnostics", {}))
            for k, history in futures.items():
                note_history(history, f"future_k{k:g}")
            states["future"] = future_rng.bit_generator.state
            audit_rng, roots["audit"] = _rng(kind, mid, 30, index, phase)
            uniforms, rejects = _uniform_open(audit_rng, count)
            numerical["open_uniform_rejections"] += rejects
            states["audit"] = audit_rng.bit_generator.state
            if kind == "ideal":
                for k, history in futures.items():
                    if not np.all(history.survives):
                        raise ArithmeticError("Ideal-silence history violated survival")
                    counts[f"ideal_silence:m{mid}:k{k:g}"] = accumulate(history.arrives_within_horizon, np.ones(count), uniforms)
            else:
                for k, history in futures.items():
                    counts[f"base:interacting:m{mid}:k{k:g}"] = accumulate(history.arrives_within_horizon, np.ones(count), uniforms)
                weights = {}
                for cell in lock["cells"]:
                    if cell["model_kind"] != "interacting" or cell["model_id"] != mid:
                        continue
                    k = cell["future_multiplier"]
                    flags = futures[k].arrives_within_horizon
                    if cell["analytic_unit_weight"]:
                        result = counts[f"base:interacting:m{mid}:k{k:g}"]
                    elif cell["analytic_unconstrained_detector"]:
                        result = AuditCounts(count, int(np.sum(flags)), 0, 0, 0., 0., {})
                    else:
                        key = (cell["emission_id"], cell["detector_id"], cell["visit_dependence"])
                        if key not in weights:
                            emission = next(e for e in protocol.emissions if e.emission_id == key[0])
                            detector = next(d for d in protocol.detectors if d.detector_id == key[1])
                            low, high, diagnostic = batch_null_weights(futures[1.], geometry, schedule, emission, detector, key[2])
                            weights[key] = (low, high)
                            numerical["source_precision_rechecks"] += diagnostic.get("source_precision_rechecks", 0)
                            boundary_rechecks.extend({"context": f"likelihood_{key}", **event} for event in diagnostic.get("recheck_events", ()))
                        low, high = weights[key]
                        result = (accumulate_bounds(flags, low, high, uniforms) if cell["bounded_weights"]
                                  else accumulate(flags, low, uniforms))
                    counts[cell["cell_id"]] = result
        states["prefix"] = prefix_rng.bit_generator.state
        elapsed = time.perf_counter() - start
        ledger.progress(job, elapsed, work, details={"group": kind, "model_id": mid, "attempts": attempts})
        payload = {"protocol_hash": lock["protocol_hash"], "group_id": f"{kind}:{mid}", "kind": kind,
                   "model_id": mid, "batch_index": index, "checkpoint_index": look, "sample_size": count,
                   "counts_by_cell": {key: asdict(value) for key, value in counts.items()},
                   "seed_roots": roots, "rng_states": states, "attempts": attempts,
                   "numerical_diagnostics": numerical, "boundary_rechecks": boundary_rechecks,
                   "history_evaluations": work, "elapsed_seconds": elapsed, "job_id": job} | extra
        identifier = f"{kind}-{mid:02d}-{index:09d}"
        digest = commit_batch(Path(lock["_output_dir"]), identifier, payload, {})
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, work, status="interrupted",
                      details={"exception": type(exc).__name__, "kind": kind, "attempts": attempts})
        raise
    ledger.finish(job, time.perf_counter() - start, work, details={"batch_id": identifier, "batch_hash": digest, "attempts": attempts})
    return payload | {"_batch_id": identifier, "_batch_hash": digest, "_arrays": {}}


def _oracle_rows(lock, objects, ledger):
    path = Path(lock["_output_dir"]) / "independent_oracles.json"
    if path.exists():
        cached = read_json_checked(path)
        if cached["protocol_hash"] != lock["protocol_hash"] or canonical_hash(cached["rows"]) != cached["content_hash"]:
            raise ValueError("Independent oracle cache hash mismatch")
        return cached["rows"]
    protocol, geometry, schedule = objects
    start, job = time.perf_counter(), ledger.start("G4", details={"protocol_hash": lock["protocol_hash"], "kind": "quadrature"})
    output, base = {}, {}
    try:
        for cell in lock["cells"]:
            if cell["model_kind"] != "independent_sites":
                continue
            mid, k = cell["model_id"], cell["future_multiplier"]
            model = replace(next(m for m in protocol.models if m.model_id == mid), future_multiplier=k)
            key = (mid, k)
            if key not in base:
                base[key] = independent_oracle(model, geometry, schedule, protocol.emissions[0], protocol.detectors[0])
            if cell["analytic_unit_weight"] or cell["analytic_unconstrained_detector"]:
                result = base[key]
            else:
                emission = next(e for e in protocol.emissions if e.emission_id == cell["emission_id"])
                detector = next(d for d in protocol.detectors if d.detector_id == cell["detector_id"])
                result = independent_oracle(model, geometry, schedule, emission, detector, cell["visit_dependence"])
            if result.status != "validated":
                raise ArithmeticError("Independent oracle requires further numerical precision")
            values = {"C": result.joint_bounds.get("C", [result.C, result.C]),
                      "R0": [result.R0.low, result.R0.high], "R": [result.R.low, result.R.high],
                      "likelihood": [result.likelihood.low, result.likelihood.high]}
            if cell["analytic_unconstrained_detector"]:
                values["R"], values["likelihood"] = [0., 1.], [0., 1.]
            output[cell["cell_id"]] = values | {"status": "validated", "estimates": {"C": result.C},
                                                "numerical_errors": result.absolute_errors, "validation": result.validation}
        write_json_atomic(path, {"protocol_hash": lock["protocol_hash"], "rows": output, "content_hash": canonical_hash(output)})
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, 0, status="failed", details={"exception": type(exc).__name__})
        raise
    ledger.finish(job, time.perf_counter() - start, 0, details={"artifact": path.name, "cells": len(output)})
    return output


def _snapshot(lock, batches, looks, oracle_rows):
    counts = _all_counts(batches)
    cells, indices = [], {}
    for original in lock["cells"]:
        cell = dict(original)
        mid, kind = cell["model_id"], cell["model_kind"]
        if kind == "independent_sites":
            cell["deterministic"] = oracle_rows[cell["cell_id"]]
        else:
            cell["survival"] = {"constant": lock["survival_constants"][str(mid)]}
            if "survival_interval_id" in cell:
                cell["survival"].update(diagnostic_cell_id=f"proposal:{mid}", interval_id=cell["survival_interval_id"])
                indices[cell["survival_interval_id"]] = looks[f"diagnostic:{mid}"]
            if kind == "ideal_silence":
                cell["ideal_silence_probability"] = lock["ideal_silence_probabilities"][str(mid)]
                cell["baseline_counts_id"] = f"base:interacting:m{mid}:k{cell['future_multiplier']:g}"
            for q, identifier in cell["interval_ids"].items():
                source = "interacting" if q == "R0" or kind == "interacting" else "ideal"
                indices[identifier] = looks[f"{source}:{mid}"]
        cells.append(cell)
    summary = summarize(counts, dict(lock, cells=cells), indices)
    reference, evidence = _reference_checks(lock, counts, looks)
    summary = replace(summary, interval_evidence=summary.interval_evidence | evidence)
    return summary, counts, reference


def _reference_checks(lock, counts, looks):
    from .theorem import continuum_mean, free_joint_cdf
    rows, evidence = [], {}
    for index, h in enumerate((.02, .5)):
        b, s = continuum_mean(h, 1), math.expm1(4 * math.log1p(h)) / 4
        row = {"h": h, "b": b, "s": s, "free_probability": -math.expm1(-b),
               "rigorous_probability_bounds": [b * math.exp(-s), -math.expm1(-b)], "free_joint_checks": []}
        for item_id, item in lock["bound_registry"]["items"].items():
            if not item_id.startswith(f"shell:{index}:"):
                continue
            data = counts[item_id]
            j = looks[f"shell:{index}"]
            pool = lock["bound_registry"]["pools"][item["pool"]]
            alpha = alpha_at_checkpoint(pool["A"], pool["M"], j)
            bound = exact_interval(data.arrivals, data.histories, alpha)
            evidence[item_id] = {"successes": data.arrivals, "trials": data.histories, "checkpoint": j,
                                 "pool": item["pool"], "alpha": alpha, "interval": [bound.low, bound.high]}
            if item["quantity"] == "shell_contact":
                row.update(trials=data.histories, contact_count=data.arrivals,
                           contact_probability_interval=[bound.low * row["free_probability"], bound.high * row["free_probability"]])
            else:
                _, _, ztext, utext = item_id.split(":")
                z, u = float(ztext[1:]), float(utext[1:])
                exact = free_joint_cdf(h, z, u, 1)
                row["free_joint_checks"].append({"item_id": item_id, "z": z, "u": u, "exact": exact,
                                                "interval": [bound.low, bound.high], "consistent": bound.low <= exact <= bound.high})
        lo, hi = row["rigorous_probability_bounds"]
        a, bnd = row["contact_probability_interval"]
        row["consistent"] = a <= hi and bnd >= lo and all(c["consistent"] for c in row["free_joint_checks"])
        rows.append(row)
    return rows, evidence


def precision_requests(summary, lock, counts, looks):
    if lock["purpose"] == "smoke":
        return set()
    requests = set()
    for row in summary.rows:
        kind, mid = row["model_kind"], row["model_id"]
        if kind == "independent_sites":
            continue
        group = f"{'ideal' if kind == 'ideal_silence' else 'interacting'}:{mid}"
        bounds, point = row["intervals"], row["estimates"]
        if point["R0"] is not None and bounds["R0"][1] - bounds["R0"][0] > .01:
            requests.add(f"interacting:{mid}")
        if row.get("analytic_unit_weight") or row.get("analytic_unconstrained_detector"):
            continue
        weighted = row.get("weighted_point_bounds", {})
        for q, tolerance in (("likelihood", .005), ("R", .005)):
            if q == "R" and all(status == "excluded" for status in row["compatibility"].values()):
                continue
            center = weighted.get(q, [point[q], point[q]])
            if center[0] is not None and max(center[0] - bounds[q][0], bounds[q][1] - center[1]) > tolerance:
                if kind == "ideal_silence" and q == "likelihood":
                    if f"diagnostic:{mid}" in looks:
                        requests.add(f"diagnostic:{mid}")
                else:
                    requests.add(group)
    # A finite-width estimate alone never turns failure of a positive into a
    # negative. If point nuisance bounds resolve the primary claim but its
    # certified intervals do not, extend the relevant original ensembles.
    primary = [r for r in summary.rows if "interacting/primary" in r.get("families", ())]
    if primary and summary.certificates["interacting/primary"]["0.05"] == "inconclusive":
        baseline = max(r["estimates"]["R0"] for r in primary)
        retained, possible = [], []
        for row in primary:
            b = row.get("weighted_point_bounds", {})
            ell = b.get("likelihood", [row["estimates"]["likelihood"]] * 2)
            risk = b.get("R", [row["estimates"]["R"]] * 2)
            if ell[0] is None or risk[0] is None:
                requests.add(f"interacting:{row['model_id']}")
                continue
            if ell[0] >= .05:
                retained.append(risk[0])
            if ell[1] >= .05:
                possible.append(risk[1])
        if possible and certify_narrowing(WeightBounds(baseline, baseline),
                                          WeightBounds(max(retained, default=0.), max(possible)), bool(retained)) != "inconclusive":
            requests.update(f"interacting:{r['model_id']}" for r in primary)
    return requests


def _recover_usage(ledger, batches, protocol_hash):
    published = {b["job_id"]: b for b in batches}
    for pending in ledger.pending_jobs():
        if pending.get("details", {}).get("protocol_hash") != protocol_hash:
            continue
        job = pending["job_id"]
        records = [r for r in ledger.records() if r["job_id"] == job]
        last = records[-1]
        payload = published.get(job, {})
        elapsed = max(last.get("elapsed_seconds", 0.), payload.get("elapsed_seconds", 0.))
        work = max(last.get("history_evaluations", 0), payload.get("history_evaluations", 0))
        ledger.finish(job, elapsed, work, status="recovered_published" if payload else "interrupted",
                      details={"recovered": True, "unmeasured_tail_possible": not bool(payload)})


def _read_state(path, protocol_hash):
    state = read_json_checked(path)
    body = {k: v for k, v in state.items() if k != "content_hash"}
    if state.get("content_hash") != canonical_hash(body) or state["protocol_hash"] != protocol_hash:
        raise ValueError("Checkpoint state hash mismatch")
    if any(not isinstance(j, int) or isinstance(j, bool) or j < 1 for j in state["looks"].values()):
        raise ValueError("Invalid checkpoint index")
    return state


def _write_state(path, protocol_hash, looks):
    body = {"protocol_hash": protocol_hash, "looks": dict(looks)}
    write_json_atomic(path, body | {"content_hash": canonical_hash(body)})


def _checked_result(path, protocol_hash):
    result = read_json_checked(path)
    if (result.get("content_hash") != canonical_hash({k: v for k, v in result.items() if k != "content_hash"})
            or result["protocol_hash"] != protocol_hash):
        raise ValueError("Confirmation content hash mismatch")
    return result


def request_precision_extension(protocol_lock, group_ids=None):
    """Queue the next frozen checkpoint without replacing prior evidence."""
    verify_protocol_lock(protocol_lock)
    root = Path(protocol_lock.get("_output_dir", "results"))
    with _run_lock(root):
        result = _checked_result(root / "confirmation.json", protocol_lock["protocol_hash"])
        selected = sorted(group_ids if group_ids is not None else _groups(protocol_lock))
        if not selected or set(selected) - set(_groups(protocol_lock)):
            raise ValueError("Unknown precision-extension group")
        body = {"protocol_hash": protocol_lock["protocol_hash"], "from_looks": result["looks"],
                "from_result_hash": result["content_hash"], "groups": selected}
        request = body | {"request_id": canonical_hash(body)}
        path = root / "precision_request.json"
        if path.exists() and read_json_checked(path) != request:
            raise ValueError("Conflicting precision-extension request")
        write_json_atomic(path, request)
    return request


def _apply_extension(root, lock):
    path = root / "precision_request.json"
    if not path.exists():
        return
    request = read_json_checked(path)
    body = {k: v for k, v in request.items() if k != "request_id"}
    if request["protocol_hash"] != lock["protocol_hash"] or request["request_id"] != canonical_hash(body):
        raise ValueError("Precision request hash mismatch")
    if set(request["groups"]) - set(_groups(lock)):
        raise ValueError("Unknown precision-extension group")
    state = _read_state(root / "run_state.json", lock["protocol_hash"])
    next_looks = {key: value + (key in request["groups"]) for key, value in request["from_looks"].items()}
    if state["looks"] not in (request["from_looks"], next_looks):
        raise ValueError("Precision request checkpoint conflict")
    final = root / "confirmation.json"
    archived = root / "completed_snapshots" / (request["from_result_hash"] + ".json")
    previous = _checked_result(final if final.exists() else archived, lock["protocol_hash"])
    if previous["content_hash"] != request["from_result_hash"] or previous["looks"] != request["from_looks"]:
        raise ValueError("Precision request evidence mismatch")
    if not archived.exists():
        write_json_atomic(archived, previous)
    final.unlink(missing_ok=True)
    _write_state(root / "run_state.json", lock["protocol_hash"], next_looks)
    write_json_atomic(root / "precision_requests" / (request["request_id"] + ".json"), request)
    path.unlink()


def run_confirmation(protocol_lock, resume, ledger):
    lock = protocol_lock
    verify_protocol_lock(lock)
    root = Path(lock.get("_output_dir", "results"))
    lock = lock | {"_output_dir": str(root.resolve())}
    with _run_lock(root):
        batches = list(load_committed_batches(root, lock["protocol_hash"]))
        if batches and not resume:
            raise ValueError("Existing confirmation: use --resume; counts cannot be reset")
        _recover_usage(ledger, batches, lock["protocol_hash"])
        _apply_extension(root, lock)
        final_path = root / "confirmation.json"
        if resume and final_path.exists():
            result = _checked_result(final_path, lock["protocol_hash"])
            state = _read_state(root / "run_state.json", lock["protocol_hash"])
            if (result["batch_hashes"] != [b["_batch_hash"] for b in batches] or result["looks"] != state["looks"]):
                raise ValueError("Confirmation evidence/batch hash mismatch")
            return result
        objects, groups = _objects(lock), _groups(lock)
        state_path = root / "run_state.json"
        if state_path.exists():
            state = _read_state(state_path, lock["protocol_hash"])
            looks = state["looks"]
        else:
            looks = {key: max((b["checkpoint_index"] for b in batches if b["group_id"] == key), default=1) for key in groups}
            _write_state(state_path, lock["protocol_hash"], looks)
        oracle_rows = _oracle_rows(lock, objects, ledger)
        while True:
            progress = {key: sum(b["sample_size"] for b in batches if b["group_id"] == key) for key in groups}
            pending = True
            while pending:
                pending = False
                for key, group in groups.items():
                    target = group["initial"] * 2**(looks[key] - 1)
                    if progress[key] >= target:
                        continue
                    pending = True
                    size = min(lock["logical_batch_size"], target - progress[key])
                    index = sum(b["group_id"] == key for b in batches)
                    batch = _compute_batch(lock, group, index, size, looks[key], objects, ledger)
                    batches.append(batch)
                    progress[key] += size
            # Canonical order makes floating aggregates identical after resume.
            batches.sort(key=lambda b: b["_batch_id"])
            summary, counts, references = _snapshot(lock, batches, looks, oracle_rows)
            requests = precision_requests(summary, lock, counts, looks)
            if lock["purpose"] != "smoke":
                requests.update(f"shell:{index}" for index, row in enumerate(references) if not row["consistent"])
            checkpoint = {"protocol_hash": lock["protocol_hash"], "looks": dict(looks), "summary": asdict(summary),
                          "reference_checks": references,
                          "precision_pending": sorted(requests), "batch_hashes": [b["_batch_hash"] for b in batches]}
            checkpoint_digest = canonical_hash(checkpoint)
            checkpoint_path = root / "summaries" / (checkpoint_digest + ".json")
            if not checkpoint_path.exists():
                write_json_atomic(checkpoint_path, checkpoint)
            write_json_atomic(root / "checkpoint_summary.json", checkpoint)
            if not requests:
                break
            for key in requests:
                looks[key] += 1
            _write_state(state_path, lock["protocol_hash"], looks)
        result = checkpoint | {"status": "smoke_complete" if lock["purpose"] == "smoke" else "numerically_complete",
                               "analysis_pending": any(c == "inconclusive" for family in summary.certificates.values() for c in family.values()),
                               "checkpoint_history": sorted(p.stem for p in (root / "summaries").glob("*.json")),
                               "batches": [{"batch_id": b["_batch_id"], "protocol_hash": b["protocol_hash"],
                                            "group_id": b["group_id"], "sample_size": b["sample_size"],
                                            "seed_roots": b["seed_roots"]} for b in batches]}
        result["execution_totals"] = {"groups": {
            key: {"sampled_histories": sum(b["sample_size"] for b in batches if b["group_id"] == key),
                  "attempted_proposals": sum(b["attempts"] for b in batches if b["group_id"] == key),
                  "history_evaluations": sum(b["history_evaluations"] + b.get("nested_history_evaluations", 0)
                                             for b in batches if b["group_id"] == key)} for key in groups}}
        result["content_hash"] = canonical_hash(result)
        write_json_atomic(final_path, result)
        return read_json_checked(final_path)
