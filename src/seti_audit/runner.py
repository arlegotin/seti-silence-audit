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
from .inference import accumulate, accumulate_bounds, certify_narrowing, summarize
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
    return groups


def _rng(kind, model_id, purpose, batch_index):
    stage = {"interacting": 4, "diagnostic": 5, "ideal": 6}[kind]
    seed = [20261101, 1, stage, model_id, purpose, batch_index]
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
    model = next(m for m in protocol.models if m.model_id == mid)
    start = time.perf_counter()
    job = ledger.start("G4" if kind == "interacting" else "G5", ensemble_id=mid,
                       details={"protocol_hash": lock["protocol_hash"], "group_id": f"{kind}:{mid}", "batch_index": index})
    work, attempts, counts, roots, states = 0, 0, {}, {}, {}
    prefix_rng, roots["prefix"] = _rng(kind, mid, 40 if kind == "diagnostic" else 50 if kind == "ideal" else 10, index)
    try:
        if kind == "diagnostic":
            clocks = sample_clock_batch(model, geometry, prefix_rng, count, "lower_cone", 0)
            history = simulate_batch(clocks, geometry)
            work += count; attempts += count
            counts[f"proposal:{mid}"] = AuditCounts(count, int(np.sum(history.survives)), 0, 0, 0., 0., {})
        else:
            if kind == "ideal":
                prefix = sample_clock_batch(model, geometry, prefix_rng, count, "ideal_silence", 0)
            else:
                remaining, birth_parts, speed_parts, gap_parts = count, [], [], []
                while remaining:
                    proposed = sample_clock_batch(model, geometry, prefix_rng, remaining, "lower_cone", 0)
                    histories = simulate_batch(proposed, geometry)
                    attempts += remaining; work += remaining
                    keep = histories.survives
                    if model.speed_id in ("S1", "S2") and not np.all(keep):
                        raise ArithmeticError("Common-speed proposal violated exact survival")
                    birth_parts.append(proposed.birth_years[keep]); speed_parts.append(proposed.speeds[keep]); gap_parts.append(proposed.speed_gaps[keep])
                    remaining -= int(np.sum(keep))
                    ledger.progress(job, time.perf_counter() - start, work,
                                    details={"group": kind, "model_id": mid, "survivors_pending": remaining, "attempts": attempts})
                prefix = ClockBatch(np.concatenate(birth_parts), np.concatenate(speed_parts), np.concatenate(gap_parts))
            future_rng, roots["future"] = _rng(kind, mid, 20, index)
            multipliers = (0., 1., 10.) if mid < 16 else (1.,)
            futures = paired_future_batches(prefix, model, geometry, future_rng, multipliers)
            work += count * len(multipliers)
            states["future"] = future_rng.bit_generator.state
            audit_rng, roots["audit"] = _rng(kind, mid, 30, index)
            uniforms, rejects = _uniform_open(audit_rng, count)
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
                            weights[key] = batch_null_weights(futures[1.], geometry, schedule, emission, detector, key[2])[:2]
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
                   "history_evaluations": work, "elapsed_seconds": elapsed, "job_id": job}
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
    return summary, counts


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
        final_path = root / "confirmation.json"
        if resume and final_path.exists():
            result = read_json_checked(final_path)
            content_hash = canonical_hash({k: v for k, v in result.items() if k != "content_hash"})
            if (result.get("content_hash") != content_hash or result["protocol_hash"] != lock["protocol_hash"]
                    or result["batch_hashes"] != [b["_batch_hash"] for b in batches]):
                raise ValueError("Confirmation evidence/batch hash mismatch")
            return result
        objects, groups = _objects(lock), _groups(lock)
        state_path = root / "run_state.json"
        if state_path.exists():
            state = read_json_checked(state_path)
            if state["protocol_hash"] != lock["protocol_hash"]:
                raise ValueError("Checkpoint state protocol mismatch")
            looks = state["looks"]
        else:
            looks = {key: max((b["checkpoint_index"] for b in batches if b["group_id"] == key), default=1) for key in groups}
            write_json_atomic(state_path, {"protocol_hash": lock["protocol_hash"], "looks": looks})
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
            summary, counts = _snapshot(lock, batches, looks, oracle_rows)
            requests = precision_requests(summary, lock, counts, looks)
            checkpoint = {"protocol_hash": lock["protocol_hash"], "looks": dict(looks), "summary": asdict(summary),
                          "precision_pending": sorted(requests), "batch_hashes": [b["_batch_hash"] for b in batches]}
            write_json_atomic(root / "checkpoint_summary.json", checkpoint)
            if not requests:
                break
            for key in requests:
                looks[key] += 1
            write_json_atomic(state_path, {"protocol_hash": lock["protocol_hash"], "looks": looks})
        result = checkpoint | {"status": "smoke_complete" if lock["purpose"] == "smoke" else "numerically_complete",
                               "analysis_pending": any(c == "inconclusive" for family in summary.certificates.values() for c in family.values()),
                               "batches": [{"batch_id": b["_batch_id"], "protocol_hash": b["protocol_hash"],
                                            "group_id": b["group_id"], "sample_size": b["sample_size"],
                                            "seed_roots": b["seed_roots"]} for b in batches]}
        result["content_hash"] = canonical_hash(result)
        write_json_atomic(final_path, result)
        return read_json_checked(final_path)
