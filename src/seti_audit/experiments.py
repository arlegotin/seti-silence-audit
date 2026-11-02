"""Development correctness controls and observational execution calibration."""

from dataclasses import asdict, replace
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np

from .artifacts import canonical_hash, write_json_atomic
from .contracts import (CalibrationResult, ClockBatch, FirstClocks, PilotResult,
                        WeightBounds)
from .detection import batch_null_weights
from .inference import accumulate, exact_interval
from .model import (_uniform_open, history_at, sample_clock_batch, sample_speed_marks,
                    simulate_batch, simulate_history)
from .oracles import independent_oracle


def _rss_bytes():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024))


def _identity(protocol, catalog, schedule):
    import hashlib
    return {"protocol_config": canonical_hash(asdict(protocol)),
            "geometry": canonical_hash({"sites": catalog.geometry.site_ids, "xyz": catalog.geometry.xyz_ly.tolist()}),
            "schedule": canonical_hash(asdict(schedule)), "source_hashes": protocol.source_hashes,
            "component_hashes": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                 for name in ("model.py", "detection.py", "oracles.py", "inference.py")},
            "phase": "development"}


def plan_precision(protocol, proposal_costs, acceptance_bounds, *, logical_batch_size=1024):
    """Plan initial precision without reducing it in response to runtime."""
    survivors = {m.model_id: protocol.initial_checkpoints["primary_survivors" if m.model_id < 16 else "age_survivors"]
                 for m in protocol.models}
    diagnostics = {m.model_id: protocol.initial_checkpoints["survival_proposals"]
                   for m in protocol.models if m.speed_id in ("S3", "S4")}
    projected = 0.
    for model in protocol.models:
        cost, acceptance = proposal_costs[model.model_id], acceptance_bounds[model.model_id]
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("Finite nonnegative measured proposal cost required")
        if acceptance.low <= 0:
            raise ArithmeticError("Additional proposal diagnostics needed for a finite conservative cost projection")
        # Cost the two additional paired continuation replays as complete
        # proposal evaluations, conservatively including unused response work.
        continuations = 3 if model.model_id < 16 else 1
        work = continuations * survivors[model.model_id] / acceptance.low + diagnostics.get(model.model_id, 0)
        if model.model_id < 16:
            work += protocol.initial_checkpoints["ideal_survivors"]
        projected += work * cost
    return CalibrationResult(survivors, diagnostics, logical_batch_size, projected,
                             proposal_costs, acceptance_bounds, {}, _rss_bytes(),
                             ("Use measured throughput to optimize and schedule every required setting.",
                              "Projection covers initial checkpoints; precision extensions continue when needed.",
                              "Runtime does not reduce the scientific matrix or precision."), ())


def _check_scalar(batch, geometry, indices):
    for index in indices:
        index = int(index)
        reference = simulate_history(FirstClocks(batch.birth_years[index], batch.speeds[index], batch.speed_gaps[index]), geometry)
        actual = history_at(batch, index)
        if (not np.array_equal(reference.accepted_indices, actual.accepted_indices)
                or not np.array_equal(reference.occupation_years, actual.occupation_years)
                or reference.arrival_year != actual.arrival_year
                or reference.survives != actual.survives
                or reference.arrives_within_horizon != actual.arrives_within_horizon):
            raise ArithmeticError("Batch/scalar pathwise disagreement")


def paired_future_batches(prefix_clocks, config, geometry, rng, multipliers=(0., 1., 10.)):
    """Reuse residual hazards and marks; past attempts stay permanently spent."""
    if np.any(np.isfinite(prefix_clocks.birth_years) & (prefix_clocks.birth_years > 0)):
        raise ValueError("Paired future requires a through-zero prefix")
    shape = prefix_clocks.birth_years.shape
    u, rejected = _uniform_open(rng, int(np.prod(shape)))
    residuals = -np.log(u).reshape(shape)
    speeds, gaps, diagnostics = sample_speed_marks(config, rng, int(np.prod(shape)))
    speeds, gaps = speeds.reshape(shape), gaps.reshape(shape)
    diagnostics["open_uniform_rejections"] += rejected
    eligible = np.isinf(prefix_clocks.birth_years)
    rate = config.mu / (len(geometry.site_ids) * config.age_years) if geometry.site_ids else 0.
    output = {}
    for k in multipliers:
        if not math.isfinite(k) or k < 0:
            raise ValueError("Invalid future multiplier")
        future = residuals / (rate * k) if rate * k > 0 else np.full(shape, np.inf)
        future[future > 100] = np.inf
        clocks = ClockBatch(np.where(eligible, future, prefix_clocks.birth_years),
                            np.where(eligible, speeds, prefix_clocks.speeds), np.where(eligible, gaps, prefix_clocks.speed_gaps),
                            {"future_multiplier": float(k), "mark_diagnostics": diagnostics})
        output[float(k)] = simulate_batch(clocks, geometry)
    return output


def calibrate(protocol, catalog, schedule, ledger, *, sizes=(1024, 4096, 16384)) -> CalibrationResult:
    if not sizes or any(not isinstance(n, int) or n <= 0 for n in sizes):
        raise ValueError("Positive measurement sizes required")
    job, start = ledger.start("G2"), time.perf_counter()
    work, records, costs, acceptance = 0, [], {}, {}
    identity = _identity(protocol, catalog, schedule)
    try:
        cold_start = time.perf_counter()
        imports = subprocess.run([sys.executable, "-c", "import numpy, scipy, seti_audit.model, seti_audit.detection"],
                                 check=True, capture_output=True, text=True)
        cold_seconds = time.perf_counter() - cold_start
        for model in protocol.models:
            samples, accepted_count, proposed_count = [], 0, 0
            for size in sizes:
                for repeat in (0, 1):
                    rng = np.random.default_rng([20261101, 0, 2, model.model_id, size, repeat])
                    tick = time.perf_counter()
                    clocks = sample_clock_batch(model, catalog.geometry, rng, size, "lower_cone", 100)
                    clocks_seconds = time.perf_counter() - tick
                    tick = time.perf_counter()
                    batch = simulate_batch(clocks, catalog.geometry)
                    propagation_seconds = time.perf_counter() - tick
                    work += size
                    tick = time.perf_counter()
                    # The full present-day response family is timed, not just a
                    # single cheap detector. E0/Duncal have analytic controls.
                    for emission in protocol.emissions:
                        if emission.zeta == 0:
                            continue
                        for detector in protocol.detectors:
                            if not detector.allow_partial:
                                batch_null_weights(batch, catalog.geometry, schedule, emission, detector)
                    selection_seconds = time.perf_counter() - tick
                    indices = np.unique(np.array([0, size // 2, size - 1]))
                    _check_scalar(batch, catalog.geometry, indices)
                    work += len(indices)
                    k = int(np.sum(batch.survives))
                    accepted_count += k; proposed_count += size
                    seconds = clocks_seconds + propagation_seconds + selection_seconds
                    samples.append(seconds / size)
                    records.append({"model_id": model.model_id, "size": size, "repeat": repeat,
                                    "clocks_seconds": clocks_seconds, "propagation_seconds": propagation_seconds,
                                    "selection_seconds": selection_seconds, "total_seconds": seconds,
                                    "accepted_proposals": k, "scalar_checks": len(indices),
                                    "scalar_rechecks": len(batch.diagnostics["scalar_rechecks"])})
            costs[model.model_id] = max(samples)
            acceptance[model.model_id] = (WeightBounds(1., 1.) if model.speed_id in ("S1", "S2")
                                          else exact_interval(accepted_count, proposed_count, .001 / len(protocol.models)))
        # Include paired replay, quadrature, and report primitives separately.
        model = protocol.models[-1]
        rng = np.random.default_rng([20261101, 0, 2, 1000])
        clocks = sample_clock_batch(model, catalog.geometry, rng, sizes[0], "lower_cone", 0)
        tick = time.perf_counter()
        paired_future_batches(clocks, model, catalog.geometry, rng)
        replay_seconds = time.perf_counter() - tick
        work += 3 * sizes[0]
        tick = time.perf_counter()
        oracle = independent_oracle(model, catalog.geometry, schedule, protocol.emissions[1], protocol.detectors[0])
        quadrature_seconds = time.perf_counter() - tick
        if oracle.status != "validated":
            raise ArithmeticError("Independent baseline needs numerical refinement")
        tick = time.perf_counter()
        with tempfile.TemporaryDirectory() as folder:
            write_json_atomic(Path(folder) / "table.json", {"records": records, "oracle": asdict(oracle)})
        serialization_seconds = time.perf_counter() - tick
        result = plan_precision(protocol, costs, acceptance)
        quadrature_projection = quadrature_seconds * 60 * len(protocol.models)
        timings = {"records": records, "cold_process_import_seconds": cold_seconds,
                   "paired_replay_seconds": replay_seconds, "paired_replay_trials": sizes[0],
                   "quadrature_seconds": quadrature_seconds, "report_serialization_seconds": serialization_seconds,
                   "quadrature_projection_seconds": quadrature_projection,
                   "full_report_timing": "pending Task 13; no complete-report timing claimed",
                   "identity": identity, "history_evaluations": work,
                   "projection_basis": "conservative per-proposal full response costs and lower acceptance bounds"}
        evidence_id = "G2:" + canonical_hash(timings)
        result = replace(result, projected_seconds=result.projected_seconds + quadrature_projection + cold_seconds,
                         timings=timings, rss_bytes=_rss_bytes(), evidence_ids=(evidence_id,))
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, work, status="failed",
                      details={"exception": type(exc).__name__, "identity": identity})
        raise
    ledger.finish(job, time.perf_counter() - start, work, details={"evidence_id": evidence_id, "rss_bytes": result.rss_bytes})
    return result


def pilot(protocol, catalog, schedule, ledger, *, n_histories=1024) -> PilotResult:
    job, start = ledger.start("G3"), time.perf_counter()
    work, diagnostics = 0, {}
    before = canonical_hash(asdict(protocol))
    identity = _identity(protocol, catalog, schedule)
    try:
        from .theorem import _evaluate_shell
        phantom = _evaluate_shell(np.array([[1., 0, 0, 0, 9.], [1.1, 0, 0, 1.1, 1 / .9 - 1]]), h=20.)
        work += 1
        dark = accumulate(np.array([True, False]), np.array([1., .06]), np.array([.5, .5]))
        positive = accumulate(np.array([True, False]), np.array([.06, 1.]), np.array([.5, .5]))
        controls = {"fast_dark": {"R0": .5, "likelihood": dark.sum_w / 2, "R": dark.sum_bw / dark.sum_w},
                    "positive": {"R0": .5, "likelihood": positive.sum_w / 2, "R": positive.sum_bw / positive.sum_w},
                    "phantom_suppressed": phantom["suppressed_count"] == 1,
                    "scalar_batch_matches": True, "null_identity": True, "paired_past_likelihood": True,
                    "common_speed_identity": True, "ideal_silence": True}
        models = [m for m in protocol.models if (m.mu == 1 and m.speed_id == "S1" and m.age_years == 10000)
                  or (m.mu == 12 and m.speed_id == "S4" and m.age_years == 10000)]
        if len(models) != 2:
            raise ValueError("Pilot requires mu=1/S1 and mu=12/S4 development settings")
        for model in models:
            rng = np.random.default_rng([20261101, 0, 3, model.model_id])
            clocks = sample_clock_batch(model, catalog.geometry, rng, n_histories, "lower_cone", 0)
            prefix = simulate_batch(clocks, catalog.geometry)
            work += n_histories
            indices = np.unique(np.linspace(0, n_histories - 1, min(13, n_histories), dtype=int))
            _check_scalar(prefix, catalog.geometry, indices)
            work += len(indices)
            future = paired_future_batches(clocks, model, catalog.geometry, rng)
            work += 3 * n_histories
            past_low, past_high, _ = batch_null_weights(prefix, catalog.geometry, schedule, protocol.emissions[1], protocol.detectors[0])
            for batch in future.values():
                low, high, _ = batch_null_weights(batch, catalog.geometry, schedule, protocol.emissions[1], protocol.detectors[0])
                controls["paired_past_likelihood"] &= bool(np.array_equal(past_low, low) and np.array_equal(past_high, high))
            current = future[1.]
            if model.speed_id == "S1":
                independent = simulate_batch(ClockBatch(current.birth_years, current.speeds, current.speed_gaps), catalog.geometry, False)
                work += n_histories
                controls["common_speed_identity"] &= bool(np.array_equal(independent.arrival_years, current.arrival_years))
            low, high, _ = batch_null_weights(current, catalog.geometry, schedule, protocol.emissions[0], protocol.detectors[0])
            controls["null_identity"] &= bool(np.all(low == 1) and np.all(high == 1))
            ideal = sample_clock_batch(model, catalog.geometry, rng, n_histories, "ideal_silence")
            ideal_history = simulate_batch(ideal, catalog.geometry)
            work += n_histories
            controls["ideal_silence"] &= bool(np.all(ideal.birth_years + catalog.geometry.radii_ly > 0)
                                               and np.all(ideal_history.survives))
            selected = prefix.survives
            diagnostics[str(model.model_id)] = {"proposals": n_histories, "surviving": int(np.sum(selected)),
                                                "R0_descriptive": float(np.mean(current.arrives_within_horizon[selected])) if np.any(selected) else None,
                                                "likelihood_bounds_descriptive": [float(np.mean(past_low[selected])), float(np.mean(past_high[selected]))] if np.any(selected) else None}
        controls["fast_dark_increases_risk"] = controls["fast_dark"]["R"] > .5
        controls["positive_reduces_risk"] = controls["positive"]["R"] < .5
        after = canonical_hash(asdict(protocol))
        controls["protocol_unchanged"] = before == after
        passed = all(value for value in controls.values() if isinstance(value, (bool, np.bool_)))
        payload = {"identity": identity, "controls": controls, "diagnostics": diagnostics,
                   "protocol_hash_before": before, "protocol_hash_after": after}
        evidence_id = "G3:" + canonical_hash(payload)
        diagnostics["identity"] = identity
        if not passed:
            raise ArithmeticError("Pilot mechanism control failed")
        result = PilotResult(True, (evidence_id,), controls, diagnostics)
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, work, status="failed",
                      details={"exception": type(exc).__name__, "identity": identity})
        raise
    ledger.finish(job, time.perf_counter() - start, work, details={"evidence_id": evidence_id})
    return result
