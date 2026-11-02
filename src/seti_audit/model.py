"""First-attempt clocks and chronological permanent birth suppression."""

import math

import numpy as np

from .contracts import FirstClocks, FloatArray, Geometry, History, ModelConfig


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
        diagnostics["speed_rounding_mass_bound"] = float(np.sum(fast)) * 2**-53 * (
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
    if conditioning != "unconditional":
        raise ValueError(f"Unsupported conditioning: {conditioning}")
    n = len(geometry.site_ids)
    uniforms, rejected = _uniform_open(rng, n)
    births = invert_hazard(-np.log(uniforms), config, n, horizon_years)
    speeds, gaps, diagnostics = sample_speed_marks(config, rng, n)
    diagnostics["open_uniform_rejections"] += rejected
    return FirstClocks(births, speeds, gaps, diagnostics)


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
