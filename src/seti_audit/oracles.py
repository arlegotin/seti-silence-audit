"""Unconditional first-clock integration for the matched independent-site model.

This model has no suppression. It deliberately does not use the interacting
survival sampler. The birth density and no-birth atom are from the original
unconditional point process; speed is integrated out before time integration.
"""

import math

import numpy as np
from scipy.integrate import quad

from .contracts import (DetectorConfig, EmissionConfig, Geometry, ModelConfig,
                        OracleResult, Schedule, WeightBounds)
from .detection import source_null_weight


def _product(values):
    return 0. if np.any(values == 0) else math.exp(math.fsum(math.log(x) for x in values))


def _difference(first, second):
    if first == 0:
        return 0.
    if second == 0:
        return first
    return first * -math.expm1(min(0., math.log(second) - math.log(first)))


def independent_product_summary(e, h, n, j, *, site_errors=None) -> OracleResult:
    """Combine site integrals; nuisance endpoints remain distinct from error.

    e/h are survival to 0/100; n/j are lower/upper null-weighted survival
    to 0/100. J and K partition the *same* weight before conservative ratios.
    """
    e, h, n, j = (np.asarray(a, dtype=float) for a in (e, h, n, j))
    if (e.ndim != 1 or h.shape != e.shape or n.shape != (e.size, 2)
            or j.shape != n.shape or any(np.any(~np.isfinite(a)) for a in (e, h, n, j))
            or any(np.any((a < 0) | (a > 1)) for a in (e, h, n, j))
            or np.any(h > e + 1e-12) or np.any(j > n + 1e-12)
            or np.any(n[:, 0] > n[:, 1]) or np.any(j[:, 0] > j[:, 1])):
        raise ValueError("Invalid independent-site integrals")
    err = np.zeros(e.size) if site_errors is None else np.asarray(site_errors, dtype=float)
    if err.shape != e.shape or np.any(~np.isfinite(err) | (err < 0)):
        raise ValueError("Invalid numerical errors")
    C, H = _product(e), _product(h)
    G = [_product(n[:, k]) for k in (0, 1)]
    K = [_product(j[:, k]) for k in (0, 1)]
    J = [_difference(G[k], K[k]) for k in (0, 1)]

    def enclosure(values):
        return (_product(np.maximum(0., values - err)),
                _product(np.minimum(1., values + err)))

    cb, hb = enclosure(e), enclosure(h)
    gb = [enclosure(n[:, k]) for k in (0, 1)]
    kb = [enclosure(j[:, k]) for k in (0, 1)]
    joint = {"C": list(cb), "H": list(hb), "G": gb, "K": kb, "J": J}
    if cb[0] <= 0:
        return OracleResult(C, WeightBounds(0., 1.), WeightBounds(0., 1.), WeightBounds(0., 1.),
                            {"likelihood": 1., "R0": 1., "R": 1.}, joint,
                            status="conditioning_unresolved")

    def clip(value):
        return min(1., max(0., value))

    r0 = _difference(C, H) / C
    R0 = WeightBounds(clip(1 - hb[1] / cb[0]), clip(1 - hb[0] / cb[1]))
    ell = WeightBounds(clip(gb[0][0] / cb[1]), clip(gb[1][1] / cb[0]))
    jl = max(0., gb[0][0] - kb[0][1])
    ju = max(0., gb[1][1] - kb[1][0])
    low = jl / (jl + kb[1][1]) if jl + kb[1][1] > 0 else 0.
    high = ju / (ju + kb[0][0]) if ju + kb[0][0] > 0 else 1.
    R = WeightBounds(clip(low), clip(high))
    central_r = (J[0] / (J[0] + K[1]) if J[0] + K[1] > 0 else 0.,
                 J[1] / (J[1] + K[0]) if J[1] + K[0] > 0 else 1.)
    errors = {"R0": max(abs(R0.low - r0), abs(R0.high - r0)),
              "likelihood": max(abs(ell.low - G[0] / C), abs(ell.high - G[1] / C)),
              "R": max(abs(R.low - central_r[0]), abs(R.high - central_r[1]))}
    # With identically unit weights, ell=1 is algebraic, not a quadrature claim.
    if np.array_equal(n[:, 0], e) and np.array_equal(n[:, 1], e) and np.array_equal(j[:, 0], h) and np.array_equal(j[:, 1], h):
        ell, R = WeightBounds(1., 1.), R0
        errors["likelihood"], errors["R"] = 0., errors["R0"]
    status = "validated" if max(errors.values()) < 1e-4 else "needs_precision"
    if G[1] == 0:
        status = "null_conditioning_undefined"
    return OracleResult(C, ell, R0, R, errors, joint, status=status)


def _speed_components(speed_id):
    return {"S1": ((1., 10.),), "S2": ((1., 2.),),
            "S3": ((.999, 10.), (.001, None)), "S4": ((1., None),)}[speed_id]


def _affine_survival(t, midpoint, radius, speed_id):
    """g(t,b)=intercept+slope*b on an interval split at every change."""
    intercept = slope = 0.
    for mass, inverse_speed in _speed_components(speed_id):
        if inverse_speed is not None:
            intercept += mass * (midpoint + inverse_speed * radius > t)
        elif t - midpoint <= radius:
            intercept += mass
        elif t - midpoint < 2 * radius:
            intercept += mass * (2 - t / radius)
            slope += mass / radius
    return intercept, slope


def _speed_survival(t, birth, radius, speed_id):
    # Direct delta evaluation is independent of the affine antiderivative.
    delta = t - birth
    return math.fsum(mass * ((birth + inverse * radius > t) if inverse is not None else
                             (1. if delta <= radius else 0. if delta >= 2 * radius else 2 - delta / radius))
                     for mass, inverse in _speed_components(speed_id))


def _birth_knots(config, radius, site_id, schedule, emission):
    points = {-config.age_years, 0., 100.}
    for t in (0., 100.):
        for _, inverse in _speed_components(config.speed_id):
            for m in ((inverse,) if inverse is not None else (1., 2.)):
                points.add(t - radius * m)
    # Eligibility depends on received endpoints crossing scan/window endpoints.
    # F1 possibility additionally changes when two ON durations fit.
    windows = [(s.start_year, math.fsum((s.start_year, s.duration_year)), s.duration_year)
               for s in schedule.exact_scans if s.site_id == site_id]
    windows += [(a, b, v.duration_year) for v in schedule.bounded_visits if v.site_id == site_id
                for a, b in v.allowed_intervals]
    for a, b, duration in windows:
        for boundary in (a, b, a + 2 * duration, b - 2 * duration):
            points.add(math.fsum((boundary, -radius, -emission.delay_years)))
            if emission.lifetime_years is not None:
                points.add(math.fsum((boundary, -radius, -emission.delay_years, -emission.lifetime_years)))
    return sorted(x for x in points if -config.age_years <= x <= 100.)


def _offset_mean(z):
    if abs(z) < .01:
        return .5 - z / 12 + z**3 / 720 - z**5 / 30240 + z**7 / 1209600
    return 1 / z - math.exp(-z) / -math.expm1(-z)


def independent_oracle(config: ModelConfig, geometry: Geometry, schedule: Schedule,
                       emission: EmissionConfig, detector: DetectorConfig,
                       visit_dependence: str = "nominal") -> OracleResult:
    """Two independent integrations of the piecewise exponential birth law."""
    count = len(geometry.site_ids)
    if not count or config.mu == 0:
        return OracleResult(1., WeightBounds(1., 1.), WeightBounds(0., 0.), WeightBounds(0., 0.),
                            {"likelihood": 0., "R0": 0., "R": 0.}, {},
                            {"methods": ["analytic_affine", "split_quad"], "max_method_disagreement": 0.})
    rate = config.mu / (count * config.age_years)
    site_results, site_errors, diagnostics = [], [], []
    for site_id, radius in zip(geometry.site_ids, geometry.radii_ly):
        radius = float(radius)
        knots = _birth_knots(config, radius, site_id, schedule, emission)
        # Order: e, h, n-, n+, j-, j+.
        atom = math.exp(-rate * (config.age_years + config.future_multiplier * 100))
        analytic, numeric = np.full(6, atom), np.full(6, atom)
        quadrature_error = 0.

        def hazard(birth):
            return rate * (min(birth, 0.) + config.age_years + config.future_multiplier * max(birth, 0.))

        for left, right in zip(knots, knots[1:]):
            if right <= left:
                continue
            midpoint = left + (right - left) / 2
            current_rate = rate * (1. if midpoint < 0 else config.future_multiplier)
            if current_rate == 0:
                continue
            w = source_null_weight(midpoint, radius, schedule, site_id, emission, detector, visit_dependence)
            mass = math.exp(-hazard(left)) * -math.expm1(-current_rate * (right - left))
            first_moment = mass * (right - left) * _offset_mean(current_rate * (right - left))
            for t, positions, multipliers in ((0., (0, 2, 3), (1., w.low, w.high)),
                                               (100., (1, 4, 5), (1., w.low, w.high))):
                intercept, slope = _affine_survival(t, midpoint, radius, config.speed_id)
                integral = (intercept + slope * left) * mass + slope * first_moment
                refined, error = quad(lambda b: current_rate * math.exp(-hazard(b)) *
                                      _speed_survival(t, b, radius, config.speed_id),
                                      left, right, epsabs=1e-13, epsrel=2e-12)
                quadrature_error += error
                for position, multiplier in zip(positions, multipliers):
                    analytic[position] += integral * multiplier
                    numeric[position] += refined * multiplier
        disagreement = float(np.max(np.abs(analytic - numeric)))
        # Covers floating endpoint placement and summation as well as both
        # integration evaluations. This is numerical width, not F1 uncertainty.
        scale = max(1., config.age_years, radius * 10, emission.delay_years,
                    emission.lifetime_years or 0., 100.)
        roundoff = 64 * np.finfo(float).eps * (len(knots) + 1) * (1 + rate * scale)
        error = disagreement + quadrature_error + roundoff
        site_results.append(np.clip(analytic, 0., 1.))
        site_errors.append(error)
        diagnostics.append({"site_id": site_id, "knots": len(knots), "error": error,
                            "method_disagreement": disagreement, "quad_error": quadrature_error})
    a = np.array(site_results)
    result = independent_product_summary(a[:, 0], a[:, 1], a[:, 2:4], a[:, 4:6], site_errors=site_errors)
    validation = {"methods": ["analytic_affine", "split_quad"],
                  "max_method_disagreement": max(d["method_disagreement"] for d in diagnostics),
                  "site_diagnostics": diagnostics}
    return OracleResult(result.C, result.likelihood, result.R0, result.R,
                        result.absolute_errors, result.joint_bounds, validation, result.status)


def ideal_silence_probability(config: ModelConfig, geometry: Geometry) -> float:
    if not geometry.site_ids:
        return 1.
    rate = config.mu / (len(geometry.site_ids) * config.age_years)
    return math.exp(-rate * math.fsum(max(config.age_years - r, 0.) for r in geometry.radii_ly))


def ideal_silence_gap(geometry: Geometry, v_max: float) -> float:
    if not 0 < v_max < 1:
        raise ValueError("Ideal gap requires a strictly subluminal speed bound")
    return min(geometry.radii_ly, default=math.inf) * (1 / v_max - 1)
