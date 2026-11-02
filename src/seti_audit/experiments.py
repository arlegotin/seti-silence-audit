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
                                 for name in ("model.py", "detection.py", "oracles.py", "inference.py",
                                              "experiments.py", "contracts.py", "theorem.py", "resources.py")},
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
    if not isinstance(n_histories, int) or isinstance(n_histories, bool) or n_histories <= 0:
        raise ValueError("Positive pilot history count required")
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


def build_matrix(protocol, schedule):
    cells = []
    def add(model, kind, k, emission, detector, *, robust=False):
        zero = detector == "Duncal_zero"
        invisible = emission == "E0" or zero
        unconstrained = detector == "Duncal"
        bounded = not invisible and not unconstrained and (schedule.schedule_grade == "coarsened_F1" or detector == "Dpositive" or robust)
        cid = f"{kind}:m{model.model_id}:k{k:g}:{emission}:{detector}" + (":robust" if robust else "")
        baseline = f"{kind if kind != 'ideal_silence' else 'interacting'}:m{model.model_id}:k{k:g}"
        families = [f"{kind}/{emission}/{detector}/k{k:g}" + ("/robust" if robust else "")]
        if model.model_id < 16:
            families.append(f"{kind}/all_civilizations/k{k:g}")
            if emission == "E1" and detector == "Dnom" and k == 1 and not robust:
                families.append(f"{kind}/primary")
            if emission != "E0" and detector in ("Dnom", "Dweak", "Dhigh", "Dpositive"):
                families.append(f"{kind}/positive_detectors/{emission}/k{k:g}")
            if unconstrained or zero:
                families.append(f"{kind}/unconstrained_detector/{emission}/k{k:g}")
        ids = {}
        if kind != "independent_sites":
            ids["R0"] = baseline + ":R0"
            if not invisible and not unconstrained:
                # Likelihood is entirely past data, shared by future replays.
                past = f"{kind}:m{model.model_id}:{emission}:{detector}" + (":robust" if robust else "")
                if bounded:
                    for q in ("null_low", "null_high"):
                        ids[q] = past + ":" + q
                    for q in ("J_low", "J_high", "K_low", "K_high"):
                        ids[q] = cid + ":" + q
                else:
                    ids.update(likelihood=past + ":likelihood", R=cid + ":R")
        row = {"cell_id": cid, "model_id": model.model_id, "model_kind": kind, "baseline_id": baseline,
               "emission_id": emission, "detector_id": detector, "future_multiplier": float(k),
               "families": families, "interval_ids": ids, "bounded_weights": bounded,
               "thresholds": list(protocol.thresholds), "schedule_grade": schedule.schedule_grade,
               "detector_grade": schedule.detector_grade, "visit_dependence": "robust" if robust else "nominal",
               "analytic_unit_weight": invisible, "analytic_unconstrained_detector": unconstrained,
               "dependence_robust_by_F1": schedule.schedule_grade == "coarsened_F1"}
        if model.speed_id in ("S3", "S4") and kind != "independent_sites":
            row["survival_interval_id"] = f"C:m{model.model_id}"
        cells.append(row)
    detectors = [d.detector_id for d in protocol.detectors]
    for model in protocol.models:
        for kind in ("interacting", "independent_sites"):
            if model.model_id >= 16:
                for detector in ("Dnom", "Dweak", "Dhigh"):
                    add(model, kind, 1., "E1", detector)
                continue
            for emission in protocol.emissions:
                if emission.emission_id == "E0":
                    add(model, kind, 1., "E0", "Dnone")
                else:
                    for detector in detectors:
                        add(model, kind, 1., emission.emission_id, detector)
                    add(model, kind, 1., emission.emission_id, "Duncal_zero")
                    if schedule.schedule_grade == "exact":
                        for detector in ("Dnom", "Dweak", "Dhigh", "Dpositive"):
                            add(model, kind, 1., emission.emission_id, detector, robust=True)
            for k in (0., 10.):
                add(model, kind, k, "E0", "Dnone")
                for detector in detectors + ["Duncal_zero"]:
                    add(model, kind, k, "E1", detector)
        if model.model_id < 16:
            for k in (0., 1., 10.):
                cid = f"ideal_silence:m{model.model_id}:k{k:g}"
                row = {"cell_id": cid, "model_id": model.model_id, "model_kind": "ideal_silence",
                       "baseline_id": f"interacting:m{model.model_id}:k{k:g}", "future_multiplier": k,
                       "emission_id": "E1", "detector_id": "perfect", "ideal_reference": True,
                       "families": [f"ideal_silence/k{k:g}"], "thresholds": list(protocol.thresholds),
                       "schedule_grade": "ideal_simultaneous", "detector_grade": "perfect_assumption",
                       "interval_ids": {"R0": f"interacting:m{model.model_id}:k{k:g}:R0", "R": cid + ":R"}}
                if model.speed_id in ("S3", "S4"):
                    row["survival_interval_id"] = f"C:m{model.model_id}"
                cells.append(row)
    return tuple(cells)


def build_bound_registry(cells):
    items = {}
    for cell in cells:
        primary = (cell["model_kind"] == "interacting" and cell["model_id"] < 16
                   and cell["emission_id"] == "E1" and cell["detector_id"] == "Dnom"
                   and cell["future_multiplier"] == 1 and cell.get("visit_dependence") == "nominal")
        for quantity, identifier in cell["interval_ids"].items():
            pool = "primary" if primary else "diagnostics"
            if identifier in items and items[identifier]["pool"] == "primary":
                pool = "primary"
            items[identifier] = {"pool": pool, "quantity": quantity}
        if "survival_interval_id" in cell:
            items[cell["survival_interval_id"]] = {"pool": "diagnostics", "quantity": "acceptance"}
    for index in (0, 1):
        items[f"shell:{index}:contact"] = {"pool": "diagnostics", "quantity": "shell_contact"}
        for z in (.25, .5, .75, 1.):
            for u in (.25, .5, .75, 1.):
                items[f"shell:{index}:z{z:g}:u{u:g}"] = {"pool": "diagnostics", "quantity": "shell_joint"}
    return {"items": items, "pools": {name: {"A": .025, "M": sum(i["pool"] == name for i in items.values())}
                                       for name in ("primary", "diagnostics")},
            "checkpoint_rule": "A/(M*j*(j+1))", "thresholds_reuse_intervals": True}


def execution_identity():
    import hashlib
    import importlib.metadata
    import platform
    names = ("contracts.py", "model.py", "detection.py", "oracles.py", "theorem.py", "inference.py",
             "experiments.py", "storage.py", "resources.py", "artifacts.py", "runner.py")
    return {"python": platform.python_version(), "architecture": platform.machine(),
            "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib", "mpmath")},
            "code_hashes": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                            for name in names if (Path(__file__).parent / name).is_file()}}


def _scientific_grid(protocol):
    expected = [(mu, 10000, speed) for mu in (.1, 1., 3., 12.) for speed in ("S1", "S2", "S3", "S4")]
    expected += [(3., age, speed) for age in (1000, 100000) for speed in ("S1", "S4")]
    actual = [(m.mu, m.age_years, m.speed_id) for m in protocol.models]
    if actual != expected or [m.model_id for m in protocol.models] != list(range(20)) or any(m.future_multiplier != 1 for m in protocol.models):
        raise ValueError("Changed scientific grid requires an explicit deviation and fresh confirmation")
    expected_emissions = [("E0", 0, 0, None, "always"), ("E1", 1, 0, None, "always"),
                          ("E2", .1, 0, None, "always"), ("E3", 1, 100, None, "always"),
                          ("E4", 1, 0, 100, "always"), ("E5", 1, 0, None, "ctmc")]
    if [(e.emission_id, e.zeta, e.delay_years, e.lifetime_years, e.activity) for e in protocol.emissions] != expected_emissions:
        raise ValueError("Changed scientific grid: emission family")
    expected_detectors = [("Dnom", .8836, .8836, False), ("Dweak", .44, .44, False),
                          ("Dhigh", .94, .94, False), ("Dpositive", .44, .94, False), ("Duncal", 0, 1, True)]
    if [(d.detector_id, d.pair_low, d.pair_high, d.allow_partial) for d in protocol.detectors] != expected_detectors:
        raise ValueError("Changed scientific grid: detector family")
    if (protocol.thresholds != (.01, .05, .1) or protocol.future_multipliers != (0, 1, 10)
            or protocol.horizon_years != 100 or protocol.error_pools != {"primary": .025, "diagnostics": .025}
            or protocol.seed_roots != {"development": [20261101, 0], "confirmation": [20261101, 1]}
            or any(e.on_fraction != .1 or e.corr_days != 1 for e in protocol.emissions)):
        raise ValueError("Changed scientific grid or uncertainty policy")
    minima = {"primary_survivors": 100000, "age_survivors": 25000, "ideal_survivors": 25000,
              "survival_proposals": 50000, "shell_histories": 10000}
    if any(protocol.initial_checkpoints.get(key, 0) < value for key, value in minima.items()):
        raise ValueError("Changed initial precision requires a justified scientific deviation")
    required = {"quadrature_absolute": 1e-8, "quadrature_relative": 1e-6,
                "validated_probability_error": 1e-4, "formula_relative": 1e-9}
    if (protocol.tolerances.get("absolute_narrowing") != .01 or protocol.tolerances.get("relative_narrowing") != .25
            or any(not 0 < protocol.tolerances.get(key, math.inf) <= value for key, value in required.items())):
        raise ValueError("Changed scientific tolerances or materiality thresholds")


def freeze_protocol(protocol, catalog, schedule, calibration, pilot, output_dir):
    import hashlib
    from .artifacts import read_json_checked
    from .data import validate_schedule
    from .model import survival_constant
    from .oracles import ideal_silence_probability
    if protocol.purpose == "research":
        _scientific_grid(protocol)
        if calibration is None or pilot is None or not pilot.passed or not calibration.evidence_ids or not pilot.evidence_ids:
            raise ValueError("Missing correctness/precision-policy evidence")
        for model in protocol.models:
            target = protocol.initial_checkpoints["primary_survivors" if model.model_id < 16 else "age_survivors"]
            if calibration.initial_survivors.get(model.model_id, 0) < target:
                raise ValueError("Cost-only precision reduction is not an execution strategy")
            if (model.speed_id in ("S3", "S4") and calibration.initial_diagnostic_proposals.get(model.model_id, 0)
                    < protocol.initial_checkpoints["survival_proposals"]):
                raise ValueError("Missing required diagnostic precision")
        identity = _identity(protocol, catalog, schedule)
        if calibration.timings.get("identity") != identity or pilot.diagnostics.get("identity") != identity:
            raise ValueError("Stale calibration/pilot evidence identity")
        correctness = read_json_checked(Path("results/correctness.json"))
        if correctness.get("status") != "passed" or any(not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha
                                                         for p, sha in correctness.get("component_hashes", {}).items()):
            raise ValueError("Stale correctness evidence")
        if not correctness.get("component_hashes"):
            raise ValueError("Missing correctness evidence")
        if catalog.provenance["source_status"] != "source_verified" or len(catalog.geometry.site_ids) != 61 or len(catalog.source_rows) != 62:
            raise ValueError("Missing verified complete catalog")
        if schedule.schedule_grade == "unavailable":
            raise ValueError("Missing schedule information")
        if schedule.schedule_grade == "exact":
            validate_schedule(schedule, catalog, schedule.provenance | {"kind": "observing_log"})
            if schedule.provenance.get("source_status") == "synthetic_control":
                raise ValueError("Synthetic schedule cannot certify research")
    if calibration is None or pilot is None:
        raise ValueError("Missing execution evidence")
    for name, expected_hash in protocol.source_hashes.items():
        if not Path(name).is_file() or hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected_hash:
            raise ValueError("Source hash mismatch")
    cells = build_matrix(protocol, schedule)
    registry = build_bound_registry(cells)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    g = catalog.geometry
    body = {"schema_version": 1, "purpose": protocol.purpose, "config": asdict(protocol),
            "thresholds": list(protocol.thresholds), "cells": list(cells), "bound_registry": registry,
            "matrix_sha256": canonical_hash({"cells": cells}), "registry_sha256": canonical_hash(registry),
            "execution_identity": execution_identity(), "catalog_provenance": catalog.provenance,
            "geometry": {"site_ids": g.site_ids, "xyz_ly": g.xyz_ly.tolist(), "radii_ly": g.radii_ly.tolist(), "distances_ly": g.distances_ly.tolist()},
            "schedule": asdict(schedule), "calibration_evidence": calibration.evidence_ids, "pilot_evidence": pilot.evidence_ids,
            "initial_survivors": {str(k): v for k, v in calibration.initial_survivors.items()},
            "initial_diagnostic_proposals": {str(k): v for k, v in calibration.initial_diagnostic_proposals.items()},
            "initial_ideal_survivors": protocol.initial_checkpoints["ideal_survivors"],
            "logical_batch_size": calibration.logical_batch_size,
            "survival_constants": {str(m.model_id): survival_constant(m, g) for m in protocol.models},
            "ideal_silence_probabilities": {str(m.model_id): ideal_silence_probability(m, g) for m in protocol.models if m.model_id < 16},
            "precision_policy": {"cumulative_multiplier": 2, "statistical_interval_width": .01,
                                 "compatibility_error_width": .005, "alpha_rule": "A/(M*j*(j+1))"},
            "rng": {"bit_generator": "PCG64", "root": [20261101, 1],
                    "stages": {"interacting": 4, "diagnostic": 5, "ideal": 6, "shell": 7},
                    "purposes": {"prefix": 10, "future": 20, "audit": 30, "diagnostic": 40, "ideal": 50, "shell": 70},
                    "identity": "[20261101,phase,stage_id,model_id,purpose_id,batch_id]"}}
    lock = body | {"protocol_hash": canonical_hash(body)}
    for path, value in ((root / "matrix.json", {"cells": cells}), (root / "bound_registry.json", registry), (root / "protocol.lock.json", lock)):
        if path.exists() and canonical_hash(read_json_checked(path)) != canonical_hash(value):
            raise ValueError("Immutable freeze conflict; preserve previous experiment")
        if not path.exists():
            write_json_atomic(path, value)
    return lock | {"_output_dir": str(root.resolve())}


def verify_protocol_lock(lock):
    import hashlib
    from .artifacts import read_json_checked
    body = {k: v for k, v in lock.items() if k != "protocol_hash" and not k.startswith("_")}
    if canonical_hash(body) != lock["protocol_hash"]:
        raise ValueError("Protocol hash mismatch")
    if execution_identity() != lock["execution_identity"]:
        raise ValueError("Execution identity changed; resume rejected")
    for name, expected in lock["config"]["source_hashes"].items():
        if not Path(name).is_file() or hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError("Source hash mismatch; frozen source input changed")
    root = Path(lock.get("_output_dir", "results"))
    matrix = read_json_checked(root / "matrix.json", lock["matrix_sha256"])
    registry = read_json_checked(root / "bound_registry.json", lock["registry_sha256"])
    if canonical_hash(matrix["cells"]) != canonical_hash(lock["cells"]) or registry != lock["bound_registry"]:
        raise ValueError("Frozen matrix/registry mismatch")
    return True


def run_confirmation(protocol_lock, resume, ledger):
    from .runner import run_confirmation as run
    return run(protocol_lock, resume, ledger)


def request_precision_extension(protocol_lock, group_ids=None):
    from .runner import request_precision_extension as request
    return request(protocol_lock, group_ids)
