"""First-attempt clocks and chronological permanent birth suppression."""

import math

import numpy as np

from .contracts import (ClockBatch, FirstClocks, FloatArray, FutureMarks, Geometry,
                        History, HistoryBatch, ModelConfig)


def _uniform_open(rng, size: int) -> tuple[FloatArray, int]:
    values = np.asarray(rng.random(size), dtype=np.float64)
    if values.shape != (size,) or np.any(~np.isfinite(values) | (values < 0) | (values > 1)):
        raise ValueError("Invalid uniform generator output")
    rejected = 0
    bad = (values == 0) | (values == 1)
    while np.any(bad):
        count = int(np.sum(bad))
        rejected += count
        values[bad] = rng.random(count)
        if np.any(~np.isfinite(values) | (values < 0) | (values > 1)):
            raise ValueError("Invalid uniform generator output")
        bad = (values == 0) | (values == 1)
    return values, rejected


def sample_speed_marks(config: ModelConfig, rng, size: int) -> tuple[FloatArray, FloatArray, dict]:
    diagnostics = {"speed_rounding_count": 0, "speed_rounding_mass_bound": 0.0,
                   "open_uniform_rejections": 0}
    if config.speed_id in {"S1", "S2"}:
        return (np.full(size, .1 if config.speed_id == "S1" else .5),
                np.full(size, 9.0 if config.speed_id == "S1" else 1.0), diagnostics)
    if config.speed_id == "S3":
        mixture, rejected = _uniform_open(rng, size)
        fast = mixture < .001
        diagnostics["open_uniform_rejections"] += rejected
    else:
        fast = np.ones(size, dtype=bool)
    q = np.full(size, 9.0)
    if np.any(fast):
        q[fast], rejected = _uniform_open(rng, int(np.sum(fast)))
        diagnostics["open_uniform_rejections"] += rejected
    # Subtraction preserves the near-light-speed gap when 1+q would round to 1.
    v = np.empty(size)
    v[fast] = 1 - q[fast] / (1 + q[fast])
    v[~fast] = .1
    rounded = v == 1
    if np.any(rounded):
        v[rounded] = np.nextafter(1.0, 0.0)
        diagnostics["speed_rounding_count"] = int(np.sum(rounded))
        # The affected uniform-q region is contained in (0,2^-53).
        diagnostics["speed_rounding_mass_bound"] = float(size) * 2**-53 * (
            .001 if config.speed_id == "S3" else 1)
    return v, q, diagnostics


def cumulative_hazard(times: FloatArray, config: ModelConfig, n_sites: int) -> FloatArray:
    times = np.asarray(times, dtype=np.float64)
    if n_sites <= 0:
        if times.size:
            raise ValueError("A positive site count is required")
        return np.empty(0)
    rate = config.mu / (n_sites * config.age_years)
    return rate * (np.clip(times + config.age_years, 0, config.age_years)
                   + config.future_multiplier * np.maximum(times, 0))


def invert_hazard(hazards: FloatArray, config: ModelConfig, n_sites: int,
                   horizon_years: float = 100) -> FloatArray:
    hazards = np.asarray(hazards, dtype=np.float64)
    if np.any(~np.isfinite(hazards) | (hazards < 0)):
        raise ValueError("Exponential hazards must be finite and nonnegative")
    if n_sites <= 0:
        if hazards.size:
            raise ValueError("A positive site count is required")
        return np.empty(0)
    births = np.full(hazards.shape, np.inf)
    rate = config.mu / (n_sites * config.age_years)
    if rate == 0:
        return births
    historical = hazards <= rate * config.age_years
    births[historical] = -config.age_years + hazards[historical] / rate
    if config.future_multiplier > 0:
        births[~historical] = ((hazards[~historical] - rate * config.age_years)
                              / (config.future_multiplier * rate))
    births[births > horizon_years] = np.inf
    return births


def sample_first_clocks(config: ModelConfig, geometry: Geometry, rng,
                        conditioning: str = "unconditional", horizon_years: float = 100) -> FirstClocks:
    n = len(geometry.site_ids)
    uniforms, rejected = _uniform_open(rng, n)
    hazard = -np.log(uniforms)
    if conditioning in {"lower_cone", "ideal_silence"}:
        inverse_speed = _floor_inverse_speed(config) if conditioning == "lower_cone" else 1.0
        origin = np.maximum(-config.age_years, -geometry.radii_ly * inverse_speed)
        hazard += cumulative_hazard(origin, config, n)
    elif conditioning != "unconditional":
        raise ValueError(f"Unsupported conditioning: {conditioning}")
    births = invert_hazard(hazard, config, n, horizon_years)
    speeds, gaps, diagnostics = sample_speed_marks(config, rng, n)
    diagnostics["open_uniform_rejections"] += rejected
    diagnostics["conditioning"] = conditioning
    return FirstClocks(births, speeds, gaps, diagnostics)


def _floor_inverse_speed(config: ModelConfig) -> float:
    return 10.0 if config.speed_id in {"S1", "S3"} else 2.0


def survival_constant(config: ModelConfig, geometry: Geometry) -> float:
    origin = np.maximum(-config.age_years, -geometry.radii_ly * _floor_inverse_speed(config))
    return math.exp(-float(np.sum(cumulative_hazard(origin, config, len(geometry.site_ids)))))


def sample_surviving_prefix(config: ModelConfig, geometry: Geometry, rng) -> tuple[History, int]:
    """Pure scalar reference; the batch owner logs returned proposal counts."""
    attempts = 0
    while True:
        clocks = sample_first_clocks(config, geometry, rng, "lower_cone", horizon_years=0)
        history = simulate_history(clocks, geometry)
        attempts += 1
        if history.survives:
            return history, attempts
        if config.speed_id in {"S1", "S2"}:
            raise ArithmeticError("A common-speed lower-cone proposal violated exact survival")


def survival_diagnostic(config: ModelConfig, geometry: Geometry, rng,
                         n_proposals: int = 50000) -> tuple[int, int, float]:
    if not isinstance(n_proposals, int) or n_proposals <= 0:
        raise ValueError("A proposal-count diagnostic needs a positive predetermined sample size")
    accepted = 0
    for _ in range(n_proposals):
        clocks = sample_first_clocks(config, geometry, rng, "lower_cone", horizon_years=0)
        accepted += int(simulate_history(clocks, geometry).survives)
    return accepted, n_proposals, survival_constant(config, geometry)


def sample_future_marks(prefix: History, config: ModelConfig, rng) -> FutureMarks:
    if np.any(np.isfinite(prefix.birth_years) & (prefix.birth_years > 0)):
        raise ValueError("Future marks require a pre-zero prefix")
    eligible = np.isposinf(prefix.birth_years)
    count = int(np.sum(eligible))
    residual = np.full(prefix.birth_years.shape, np.inf)
    uniforms, rejected = _uniform_open(rng, count)
    residual[eligible] = -np.log(uniforms)
    speeds, gaps = prefix.speeds.copy(), prefix.speed_gaps.copy()
    speeds[eligible], gaps[eligible], diagnostics = sample_speed_marks(config, rng, count)
    diagnostics["open_uniform_rejections"] += rejected
    return FutureMarks(residual, speeds, gaps, diagnostics)


def replay_future(prefix: History, config: ModelConfig, geometry: Geometry,
                   marks: FutureMarks, k: float) -> History:
    if not math.isfinite(k) or k < 0:
        raise ValueError("Future rate multiplier must be finite and nonnegative")
    if (np.any(np.isfinite(prefix.birth_years) & (prefix.birth_years > 0))
            or not prefix.survives):
        raise ValueError("Future replay requires a surviving pre-zero prefix")
    if len(marks.residual_hazards) != len(geometry.site_ids):
        raise ValueError("Future marks and geometry have different site counts")
    births, speeds, gaps = prefix.birth_years.copy(), prefix.speeds.copy(), prefix.speed_gaps.copy()
    eligible = np.isposinf(births)
    births[eligible] = np.inf
    n = len(geometry.site_ids)
    rate = config.mu / (n * config.age_years) if n else 0.0
    if k > 0 and rate > 0:
        births[eligible] = marks.residual_hazards[eligible] / (k * rate)
        births[births > 100] = np.inf
    speeds[eligible], gaps[eligible] = marks.speeds[eligible], marks.speed_gaps[eligible]
    diagnostics = prefix.diagnostics | {"future_multiplier": float(k),
                                        "future_mark_diagnostics": marks.diagnostics}
    return simulate_history(FirstClocks(births, speeds, gaps, diagnostics), geometry)


def _flag_tolerance(*times: float) -> float:
    return max(1e-12, 64 * np.finfo(float).eps * max(1, *(abs(t) for t in times if math.isfinite(t))))


def _mp_front(source, target, clocks, geometry, mp):
    distance = mp.sqrt(sum((mp.mpf(float(x)) - mp.mpf(float(y)))**2
                           for x, y in zip(geometry.xyz_ly[source], geometry.xyz_ly[target])))
    return mp.mpf(float(clocks.birth_years[source])) + distance * (1 + mp.mpf(float(clocks.speed_gaps[source])))


def simulate_history(clocks: FirstClocks, geometry: Geometry, intersite: bool = True) -> History:
    if len(clocks.birth_years) != len(geometry.site_ids):
        raise ValueError("Clock and geometry site counts disagree")
    n = len(geometry.site_ids)
    finite = np.flatnonzero(np.isfinite(clocks.birth_years) & (clocks.birth_years <= 100))
    order = sorted(finite, key=lambda i: (clocks.birth_years[i], geometry.site_ids[i]))
    occupation = np.full(n, np.inf)
    accepted, suppressed, flags = [], [], []
    arrival = np.inf
    arithmetic_scale = 1.0
    for i in order:
        birth = float(clocks.birth_years[i])
        keep = birth < occupation[i]
        if (intersite and math.isfinite(occupation[i])
                and abs(birth - occupation[i]) <= _flag_tolerance(birth, occupation[i], arithmetic_scale)):
            import mpmath as mp
            with mp.workdps(80):
                exact_occupation = min(_mp_front(j, i, clocks, geometry, mp) for j in accepted)
                keep = bool(mp.mpf(birth) < exact_occupation)
                flags.append({"kind": "occupation", "site_id": geometry.site_ids[i],
                              "birth_year": birth, "occupation_mp": str(exact_occupation), "accepted": keep})
        if intersite and not keep:
            suppressed.append(int(i))
            continue
        accepted.append(int(i))
        q = clocks.speed_gaps[i]
        # q is authoritative; the displayed float v can round near c.
        earth = (birth + geometry.radii_ly[i]) + geometry.radii_ly[i] * q
        arrival = min(arrival, float(earth))
        if intersite:
            fronts = (birth + geometry.distances_ly[i]) + geometry.distances_ly[i] * q
            occupation = np.minimum(occupation, fronts)
            # A near-zero front may cancel two large terms. Its error scale
            # depends on those operands, not only the rounded final time.
            arithmetic_scale = max(arithmetic_scale, abs(birth),
                                   float(np.max(geometry.distances_ly[i] * (1 + q))))
        else:
            occupation[i] = birth
    survives = arrival > 0
    within = 0 < arrival <= 100
    censored = arrival > 100
    if accepted:
        relevant = [float(clocks.birth_years[i]) for i in accepted]
        relevant += [float(geometry.radii_ly[i] * (1 + clocks.speed_gaps[i])) for i in accepted]
        tolerance = _flag_tolerance(arrival, 100, *relevant)
        if abs(arrival) <= tolerance or abs(arrival - 100) <= tolerance:
            import mpmath as mp
            with mp.workdps(80):
                exact = min(mp.mpf(float(clocks.birth_years[i])) + mp.mpf(float(geometry.radii_ly[i]))
                            * (1 + mp.mpf(float(clocks.speed_gaps[i]))) for i in accepted)
                survives, within, censored = bool(exact > 0), bool(0 < exact <= 100), bool(exact > 100)
                arrival = float(exact)
                flags.append({"kind": "earth_arrival", "arrival_mp": str(exact),
                              "survives": survives, "arrives_within_horizon": within})
    diagnostics = clocks.diagnostics | {"suppressed_indices": suppressed, "flagged_comparisons": flags,
                                        "survives": survives, "arrives_within_horizon": within,
                                        "speed_gap_authoritative": True}
    return History(np.array(accepted, dtype=np.int64), clocks.birth_years, clocks.speeds, clocks.speed_gaps,
                   occupation, arrival, censored, diagnostics)


def sample_clock_batch(config: ModelConfig, geometry: Geometry, rng, n_histories: int,
                       conditioning="unconditional", horizon_years=100) -> ClockBatch:
    if not isinstance(n_histories, int) or n_histories < 0:
        raise ValueError("Nonnegative batch length required")
    sites = len(geometry.site_ids)
    uniforms, rejected = _uniform_open(rng, n_histories * sites)
    hazards = -np.log(uniforms).reshape(n_histories, sites)
    if conditioning in {"lower_cone", "ideal_silence"}:
        inverse = _floor_inverse_speed(config) if conditioning == "lower_cone" else 1.
        origin = np.maximum(-config.age_years, -geometry.radii_ly * inverse)
        hazards += cumulative_hazard(origin, config, sites)
    elif conditioning != "unconditional":
        raise ValueError("Unknown batch clock conditioning")
    births = invert_hazard(hazards.ravel(), config, sites, horizon_years).reshape(n_histories, sites)
    speeds, gaps, diagnostics = sample_speed_marks(config, rng, n_histories * sites)
    diagnostics["open_uniform_rejections"] += rejected
    diagnostics["conditioning"] = conditioning
    return ClockBatch(births, speeds.reshape(births.shape), gaps.reshape(births.shape), diagnostics)


def simulate_batch(clocks: ClockBatch, geometry: Geometry, intersite: bool = True) -> HistoryBatch:
    """Rank-wise propagation using O(batch*sites) working arrays.

    Each flagged history is independently recomputed by the scalar reference,
    including original-operand high-precision boundary comparisons.
    """
    births, gaps = clocks.birth_years, clocks.speed_gaps
    count, sites = births.shape
    if sites != len(geometry.site_ids):
        raise ValueError("Clock/geometry batch site mismatch")
    site_rank = np.argsort(np.argsort(np.array(geometry.site_ids)))
    order = np.lexsort((np.broadcast_to(site_rank, births.shape), births), axis=1)
    accepted = np.zeros(births.shape, dtype=bool)
    occupation = np.full(births.shape, np.inf)
    arrival = np.full(count, np.inf)
    scale = np.ones(count)
    flags = np.zeros(count, dtype=bool)
    rows = np.arange(count)
    for rank in range(sites):
        indices = order[:, rank]
        b = births[rows, indices]
        finite = np.isfinite(b) & (b <= 100)
        if not np.any(finite):
            break
        keep = finite.copy()
        if intersite:
            previous = occupation[rows, indices]
            tolerance = np.maximum(1e-12, 64 * np.finfo(float).eps * np.maximum.reduce((np.abs(b), np.abs(previous), scale)))
            # Exclude infinities before subtraction, avoiding spurious warnings.
            compare = finite & np.isfinite(previous)
            flagged = np.zeros(count, dtype=bool)
            flagged[compare] = np.abs(b[compare] - previous[compare]) <= tolerance[compare]
            flags |= flagged
            keep &= b < previous
        chosen = rows[keep]
        index = indices[keep]
        if not len(chosen):
            continue
        accepted[chosen, index] = True
        radius, q = geometry.radii_ly[index], gaps[chosen, index]
        earth = (b[keep] + radius) + radius * q
        arrival[chosen] = np.minimum(arrival[chosen], earth)
        if intersite:
            distances = geometry.distances_ly[index]
            fronts = (b[keep, None] + distances) + distances * q[:, None]
            occupation[chosen] = np.minimum(occupation[chosen], fronts)
            scale[chosen] = np.maximum.reduce((scale[chosen], np.abs(b[keep]), np.max(distances * (1 + q[:, None]), axis=1)))
        else:
            occupation[chosen, index] = b[keep]
    survives, within, censored = arrival > 0, (arrival > 0) & (arrival <= 100), arrival > 100
    if sites:
        operand_scale = np.maximum(np.max(np.where(accepted, np.abs(births), 0.), axis=1),
                                   np.max(np.where(accepted, geometry.radii_ly * (1 + gaps), 0.), axis=1))
        tolerance = np.maximum(1e-12, 64 * np.finfo(float).eps * np.maximum(100., operand_scale))
        flags |= np.isfinite(arrival) & ((np.abs(arrival) <= tolerance) | (np.abs(arrival - 100) <= tolerance))
    rechecks = {}
    for i in np.flatnonzero(flags):
        scalar = simulate_history(FirstClocks(births[i], clocks.speeds[i], gaps[i]), geometry, intersite)
        accepted[i] = False
        accepted[i, scalar.accepted_indices] = True
        occupation[i], arrival[i] = scalar.occupation_years, scalar.arrival_year
        survives[i], within[i], censored[i] = scalar.survives, scalar.arrives_within_horizon, scalar.right_censored
        rechecks[str(i)] = scalar.diagnostics
    for array in (order, accepted, occupation, arrival, survives, within, censored):
        array.setflags(write=False)
    return HistoryBatch(births, clocks.speeds, gaps, order, accepted, occupation, arrival,
                        censored, survives, within,
                        {"scalar_rechecks": rechecks, "batch_clock_diagnostics": clocks.diagnostics,
                         "intersite": intersite})


def history_at(batch: HistoryBatch, index: int) -> History:
    if not 0 <= index < len(batch.arrival_years):
        raise IndexError("History index outside batch")
    order = batch.candidate_order[index]
    accepted = order[batch.accepted_mask[index, order]]
    diagnostics = batch.diagnostics.get("scalar_rechecks", {}).get(str(index), {}) | {
        "batch_clock_diagnostics": batch.diagnostics.get("batch_clock_diagnostics", {}),
        "survives": bool(batch.survives[index]), "arrives_within_horizon": bool(batch.arrives_within_horizon[index])}
    return History(accepted, batch.birth_years[index], batch.speeds[index], batch.speed_gaps[index],
                   batch.occupation_years[index], float(batch.arrival_years[index]), bool(batch.right_censored[index]), diagnostics)


def simulate_microbatches(clocks: ClockBatch, geometry: Geometry, *, available_bytes: int,
                          intersite=True) -> HistoryBatch:
    """Adapt scratch space; retained logical clocks/draws remain unchanged."""
    from .resources import physical_batch_size
    count, sites = clocks.birth_years.shape
    if count == 0:
        return simulate_batch(clocks, geometry, intersite)
    size = physical_batch_size(count, bytes_per_history=max(1, sites) * 128, available_bytes=available_bytes)
    parts = []
    rechecks = {}
    for offset in range(0, count, size):
        end = min(count, offset + size)
        subclocks = ClockBatch(clocks.birth_years[offset:end], clocks.speeds[offset:end], clocks.speed_gaps[offset:end])
        part = simulate_batch(subclocks, geometry, intersite)
        rechecks.update({str(int(i) + offset): value for i, value in part.diagnostics["scalar_rechecks"].items()})
        parts.append(part)
    def join(name):
        result = np.concatenate([getattr(p, name) for p in parts])
        result.setflags(write=False)
        return result
    return HistoryBatch(clocks.birth_years, clocks.speeds, clocks.speed_gaps,
                        *(join(name) for name in ("candidate_order", "accepted_mask", "occupation_years", "arrival_years",
                                                  "right_censored", "survives", "arrives_within_horizon")),
                        {"scalar_rechecks": rechecks, "batch_clock_diagnostics": clocks.diagnostics, "intersite": intersite,
                         "physical_batch_size": size})
