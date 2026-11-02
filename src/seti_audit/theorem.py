"""Independent finite-age reference checks for the supplied continuum note.

Kernel: source E10. Warning intensity: blueprint's independent repair from E8,
not a transcription of the damaged display. These are continuum references,
not formulas for the finite stellar catalog or the actual telescope survey.
"""

import hashlib
import math
from pathlib import Path

import mpmath as mp
from scipy.integrate import quad

from .artifacts import write_json_atomic


def _validate(h, T, d, intensity=1., alpha=1.):
    if (not all(math.isfinite(x) for x in (h, T, intensity, alpha)) or h < 0
            or T <= 0 or intensity < 0 or alpha <= 0 or not isinstance(d, int) or d < 1):
        raise ValueError("Invalid continuum parameters")


def finite_age_kernel(q: float, h: float, T: float, d: int) -> float:
    _validate(h, T, d)
    if not math.isfinite(q) or q <= 0:
        raise ValueError("Speed gap must be strictly positive")
    if q >= h / T:
        return h**(d + 1) / q**d
    return T**(d + 1) * math.expm1((d + 1) * math.log1p(h / T) - d * math.log1p(q))


def _tail_moment(a, alpha, d):
    if a >= 1:
        return 0.
    power = alpha - d
    return alpha * (-math.log(a) if power == 0 else -math.expm1(power * math.log(a)) / power)


def continuum_mean(h: float, alpha: float, T: float = 1., d: int = 3,
                   intensity: float = 1.) -> float:
    _validate(h, T, d, intensity, alpha)
    if h == 0 or intensity == 0:
        return 0.
    delta = h / T
    split = min(delta, 1.)
    # Integrate a normalized O(1) function with the exact power-law weight.
    low, _ = quad(lambda x: alpha * math.expm1((d + 1) * math.log1p(delta)
                                              - d * math.log1p(split * x)) / delta,
                  0, 1, weight="alg", wvar=(alpha - 1, 0), epsabs=2e-13, epsrel=2e-13)
    return intensity / (d + 1) * (T**d * h * split**alpha * low
                                  + h**(d + 1) * _tail_moment(split, alpha, d))


def warning_intensity(h: float, u: float, alpha: float, T: float = 1., d: int = 3,
                      intensity: float = 1.) -> float:
    _validate(h, T, d, intensity, alpha)
    if not 0 <= u <= 1:
        raise ValueError("Warning fraction must be in [0,1]")
    if h == 0 or u == 0 or intensity == 0:
        return 0.
    split = min(u * h / (T + (1 - u) * h), 1.)
    integral, _ = quad(lambda x: alpha * (1 + split * x)**(-d), 0, 1,
                       weight="alg", wvar=(alpha - 1, 0), epsabs=2e-13, epsrel=2e-13)
    return intensity * ((T + h)**d * split**alpha * integral
                        + (u * h)**d * _tail_moment(split, alpha, d))


def free_joint_cdf(h: float, z: float, u: float, alpha: float) -> float:
    if h <= 0 or not 0 <= z <= 1 or not 0 <= u <= 1:
        raise ValueError("Conditional CDF needs h>0 and fractions in [0,1]")
    if z == 0 or u == 0:
        return 0.
    normalizer = -math.expm1(-continuum_mean(h, alpha))
    if u == 1:
        return -math.expm1(-continuum_mean(z * h, alpha)) / normalizer
    result, _ = quad(lambda y: math.exp(-continuum_mean(h * y, alpha)) *
                     warning_intensity(h * y, u, alpha) * h / normalizer,
                     0, z, epsabs=1e-12, epsrel=1e-11)
    return min(1., max(0., result))


def leading_mean(h, alpha, T=1., d=3, intensity=1.):
    _validate(h, T, d, intensity, alpha)
    if alpha < d:
        return intensity * d / ((d - alpha) * (alpha + 1)) * T**(d - alpha) * h**(alpha + 1)
    if alpha == d:
        return intensity * d / (d + 1) * h**(d + 1) * math.log(T / h)
    return intensity * alpha / ((d + 1) * (alpha - d)) * h**(d + 1)


def _atomic_mean(h, atoms, T=1., d=3, intensity=1.):
    return intensity / (d + 1) * math.fsum(mass * finite_age_kernel(q, h, T, d) for q, mass in atoms)


def _atomic_warning(h, u, atoms, T=1., d=3, intensity=1.):
    if u == 0:
        return 0.
    split = u * h / (T + (1 - u) * h)
    return intensity * math.fsum(mass * ((T + h)**d / (1 + q)**d if q <= split
                                        else (u * h)**d / q**d) for q, mass in atoms)


def high_precision_mean(h, alpha, *, dps=80) -> str:
    """Direct E10 evaluation, with a probability-coordinate low integral.

    Returning decimal text preserves the requested precision outside workdps.
    Unlike binary64, this evaluation subtracts the original two finite-age
    powers, providing an independent cancellation-sensitive comparison.
    """
    with mp.workdps(dps):
        horizon, a = mp.mpf(str(h)), mp.mpf(str(alpha))
        if horizon <= 0 or a <= 0:
            raise ValueError("Positive h and alpha required")
        split = min(horizon, mp.mpf(1))
        low = split**a * mp.quad(lambda y: (1 + horizon)**4 / (1 + split * y**(1 / a))**3 - 1, [0, 1])
        power = a - 3
        tail = a * (-mp.log(split) if power == 0 else (1 - split**power) / power)
        return mp.nstr((low + horizon**4 * tail) / 4, dps)


def check_theorem(source: Path, out: Path) -> dict:
    alphas, horizons = (.5, 1, 2, 3, 4, 6), (1e-2, 1e-4, 1e-6, 1e-8, 1e-12)
    ratios, hp_checks, derivatives, radial_errors, closed_errors = [], [], [], [], []
    for alpha in alphas:
        for h in horizons:
            exact = continuum_mean(h, alpha)
            lead = leading_mean(h, alpha)
            row = {"alpha": alpha, "h": h, "exact": exact, "leading": lead, "ratio": exact / lead}
            if h in (1e-8, 1e-12):
                a80, a120 = high_precision_mean(h, alpha, dps=80), high_precision_mean(h, alpha, dps=120)
                with mp.workdps(130):
                    convergence = abs(mp.mpf(a80) / mp.mpf(a120) - 1)
                    float_error = abs(mp.mpf(exact) / mp.mpf(a120) - 1)
                    hp_checks.append({"alpha": alpha, "h": h, "at_80": a80, "at_120": a120,
                                      "convergence_relative": mp.nstr(convergence, 12),
                                      "binary64_relative": float(float_error)})
                    if convergence > mp.mpf('1e-60') or float_error > mp.mpf('1e-9'):
                        raise ArithmeticError("High-precision reference has not converged")
                row["precision_verified"] = True
            ratios.append(row)
        h, step = .1, 1e-5
        derivative = (continuum_mean(h - 2 * step, alpha) - 8 * continuum_mean(h - step, alpha)
                      + 8 * continuum_mean(h + step, alpha) - continuum_mean(h + 2 * step, alpha)) / (12 * step)
        derivatives.append(abs(derivative / warning_intensity(h, 1, alpha) - 1))
    for q in (.01, .1, 1.):
        upper = 1.1 / (1 + q)
        radial, _ = quad(lambda r: 3 * r**2 * max(0., 1.1 - (1 + q) * r - max(0., 1 - r)),
                         0, upper, points=[x for x in (1., .1 / q) if 0 < x < upper], epsabs=1e-14)
        radial_errors.append(abs(radial / (finite_age_kernel(q, .1, 1, 3) / 4) - 1))
    for h in (.001, .1, .5):
        closed_errors.extend([abs(continuum_mean(h, 1) / (.75 * h**2 + .5 * h**3) - 1),
                              abs(continuum_mean(h, 2) / (h**3 - .25 * h**4) - 1)])
    if max(derivatives + radial_errors + closed_errors) >= 1e-9:
        raise ArithmeticError("Independent ordinary-scale formulas disagree")
    result = {"status": "validated", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "source_scripts_reproduced": False, "warning_formula": "independent repair from E8; blueprint section 3.3",
              "ratios": ratios, "warning_derivative_max_relative_error": max(derivatives),
              "radial_max_relative_error": max(radial_errors), "closed_form_max_relative_error": max(closed_errors),
              "precision": {"digits": [80, 120], "convergence_relative_tolerance": "1e-60", "checks": hp_checks},
              "ordinary_formula_relative_tolerance": 1e-9,
              "interpretation": "Finite-age continuum consistency checks; no catalog/empirical forecast asserted."}
    write_json_atomic(out / "deterministic.json", result)
    return result
