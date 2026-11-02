"""Independent finite-age reference checks for the supplied continuum note.

Kernel: source E10. Warning intensity: blueprint's independent repair from E8,
not a transcription of the damaged display. These are continuum references,
not formulas for the finite stellar catalog or the actual telescope survey.
"""

import hashlib
import math
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from scipy.integrate import quad

from .artifacts import write_json_atomic
from .contracts import ShellSummary
from .model import _uniform_open


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


def _positive_poisson(b, uniform):
    """One-uniform inverse of Poisson(b) conditional on a positive count."""
    if not math.isfinite(b) or b <= 0 or not 0 < uniform < 1:
        raise ValueError("Positive mean and open-interval uniform required")
    probability = b / math.expm1(b)
    cumulative, k = probability, 1
    while True:
        if abs(uniform - cumulative) < 64 * np.finfo(float).eps * (k + 1):
            # No rounded CDF cutoff and no artificial maximum random count.
            with mp.workdps(80):
                rate, u = mp.mpf(b), mp.mpf(float(uniform))
                p, count = rate / mp.expm1(rate), 1
                cdf = p
                while u > cdf:
                    count += 1
                    p *= rate / count
                    cdf += p
                return count
        if uniform <= cumulative:
            return k
        k += 1
        probability *= b / k
        cumulative += probability


def _evaluate_shell(points, h, T=1.):
    """Chronological continuum points, each a distinct birth (x,y,z,t,q).

    No stellar first-clock reduction is applied. After the horizon, only a
    censoring statement is valid, since the omitted outside-shell sources can
    change the global first arrival there.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 5 or not len(points) or np.any(~np.isfinite(points)) or np.any(points[:, 4] <= 0):
        raise ValueError("Finite marked continuum points required")
    radii = np.linalg.norm(points[:, :3], axis=1)
    signals = points[:, 3] + radii
    arrivals = signals + radii * points[:, 4]
    winner = int(np.argmin(arrivals))
    accepted, rechecks = [], 0
    for i in sorted(range(len(points)), key=lambda j: (points[j, 3], j)):
        keep = True
        for j in accepted:
            distance = float(np.linalg.norm(points[j, :3] - points[i, :3]))
            front = math.fsum((points[j, 3], distance, distance * points[j, 4]))
            if abs(points[i, 3] - front) < 1e-12 * max(1., abs(front), distance):
                with mp.workdps(80):
                    dist = mp.sqrt(sum((mp.mpf(float(x)) - mp.mpf(float(y)))**2
                                       for x, y in zip(points[j, :3], points[i, :3])))
                    covered = mp.mpf(float(points[i, 3])) >= mp.mpf(float(points[j, 3])) + dist * (1 + mp.mpf(float(points[j, 4])))
                rechecks += 1
            else:
                covered = points[i, 3] >= front
            if covered:
                keep = False
                break
        if keep:
            accepted.append(i)
    accepted_winner = min(accepted, key=lambda i: arrivals[i])
    first_accepted = min(accepted, key=lambda i: signals[i])
    first_potential = int(np.argmin(signals))
    def relative_arrival(i):
        return math.fsum((float(points[i,3]), float(radii[i]), float(radii[i]*points[i,4]), -T))
    def relative_signal(i):
        return math.fsum((float(points[i,3]), float(radii[i]), -T))
    free_delay, accepted_delay = relative_arrival(winner), relative_arrival(accepted_winner)
    free_signal = relative_signal(winner)
    first_signal = relative_signal(first_accepted)
    first_potential_signal = relative_signal(first_potential)
    free_warning = float(radii[winner]*points[winner,4]/free_delay) if free_delay>0 else None
    accepted_warning = (accepted_delay-first_signal)/accepted_delay if accepted_delay>0 else None
    contact = accepted_delay <= h
    tied = np.any(np.abs(np.delete(arrivals,winner)-arrivals[winner]) <= 1e-12*max(1.,abs(arrivals[winner])))
    near = (tied or min(abs(free_delay),abs(free_delay-h),abs(accepted_delay),abs(accepted_delay-h))<1e-12
            or any(value is not None and min(abs(value),abs(1-value))<1e-12 for value in (free_warning,accepted_warning)))
    if near:
        with mp.workdps(80):
            precise_signals = [mp.mpf(float(p[3]))+mp.sqrt(sum(mp.mpf(float(x))**2 for x in p[:3])) for p in points]
            precise_arrivals = [d+mp.sqrt(sum(mp.mpf(float(x))**2 for x in p[:3]))*mp.mpf(float(p[4]))
                                for p,d in zip(points,precise_signals)]
            winner = min(range(len(points)),key=lambda i:precise_arrivals[i])
            a=precise_arrivals[winner];ah=min(precise_arrivals[i] for i in accepted)
            dh=min(precise_signals[i] for i in accepted)
            exact_free,exact_accepted=a-mp.mpf(T),ah-mp.mpf(T)
            # Subtract before rounding an absolute arrival to binary64.
            free_delay,accepted_delay=float(exact_free),float(exact_accepted)
            free_signal=float(precise_signals[winner]-mp.mpf(T))
            first_signal=float(dh-mp.mpf(T));first_potential_signal=float(min(precise_signals)-mp.mpf(T))
            free_warning=float((a-precise_signals[winner])/exact_free) if exact_free>0 else None
            accepted_warning=float((ah-dh)/exact_accepted) if exact_accepted>0 else None
            contact=bool(exact_accepted<=mp.mpf(h))
        rechecks += 1
    return {"accepted_indices": accepted, "suppressed_count": len(points) - len(accepted),
            "free_arrival_delay": free_delay, "free_source_signal_delay": free_signal,
            "first_potential_signal_delay": first_potential_signal,
            "first_accepted_signal_delay": first_signal,
            "arrival_delay": accepted_delay if contact else None, "right_censored": not contact,
            "free_warning_fraction": free_warning,
            "accepted_warning_fraction": accepted_warning if contact else None,
            "precision_rechecks": rechecks}


def _free_joint_flags(points, h, trial):
    """Compare near-boundary free events before rounded normalization."""
    grid=(.25,.5,.75,1.)
    zvalue=trial['free_arrival_delay']/h;uvalue=trial['free_warning_fraction']
    flags={f'z{z:g}:u{u:g}':bool(zvalue<=z and uvalue<=u) for z in grid for u in grid}
    recheck=None
    if any(abs(zvalue-z)<1e-12 or abs(uvalue-z)<1e-12 for z in grid):
        with mp.workdps(80):
            radii=[mp.sqrt(sum(mp.mpf(float(x))**2 for x in p[:3])) for p in points]
            signals=[mp.mpf(float(p[3]))+r for p,r in zip(points,radii)]
            arrivals=[d+r*mp.mpf(float(p[4])) for p,r,d in zip(points,radii,signals)]
            winner=min(range(len(points)),key=lambda i:arrivals[i]);delay=arrivals[winner]-1
            warning=arrivals[winner]-signals[winner]
            flags={f'z{z:g}:u{u:g}':bool(delay<=mp.mpf(h)*mp.mpf(z) and warning<=mp.mpf(u)*delay)
                   for z in grid for u in grid}
            recheck={'free_delay_mp':str(delay),'own_warning_mp':str(warning),'comparisons':dict(flags)}
    # This target is known analytically from C_h and the guaranteed B_h point.
    # It is a deterministic control, not a rounded empirical-CDF estimate.
    flags['z1:u1']=True
    return flags,recheck


def shell_joint_count(summary, z, u):
    if z==1 and u==1:
        return summary.trials
    saved=summary.diagnostics.get('free_joint_counts',{})
    key=f'z{z:g}:u{u:g}'
    if key in saved:return int(saved[key])
    return int(np.sum((summary.free_horizon_fractions<=z)&(summary.free_warning_fractions<=u)))


def _restricted_points(rng, count, h, in_B, probability, counter):
    selected, remaining = [], count
    span = math.expm1(4 * math.log1p(h))
    while remaining:
        # An expected proposal batch size, never an attempt or precision cap.
        size = max(32, math.ceil(1.2 * remaining / probability))
        u, rejected = _uniform_open(rng, size * 3)
        u = u.reshape(size, 3)
        counter["open_uniform_rejections"] += rejected
        D = np.exp(np.log1p(u[:, 0] * span) / 4)
        radius = D * u[:, 1]**(1 / 3)
        q = u[:, 2]  # alpha=1, independent of geometry and birth time.
        is_B = D - 1 + q * radius <= h
        directions = rng.normal(size=(size, 3))
        norms = np.linalg.norm(directions, axis=1)
        while np.any(norms == 0):
            mask = norms == 0
            directions[mask] = rng.normal(size=(int(np.sum(mask)), 3))
            norms[mask] = np.linalg.norm(directions[mask], axis=1)
        xyz = directions / norms[:, None] * radius[:, None]
        points = np.column_stack((xyz, D - radius, q))[is_B == in_B]
        take = min(remaining, len(points))
        if take:
            selected.append(points[:take])
            remaining -= take
        counter["point_proposals"] += size
    return np.concatenate(selected) if selected else np.empty((0, 5))


def sample_shell(config: dict, rng, n_histories: int, ledger) -> ShellSummary:
    h = config.get("h")
    if (config.get("alpha") != 1 or h not in (.02, .5) or config.get("T", 1) != 1
            or config.get("d", 3) != 3 or config.get("intensity", 1) != 1):
        raise ValueError("Validated shell construction requires alpha=1, h=.02 or .5, T=1, d=3, intensity=1")
    if not isinstance(n_histories, int) or n_histories <= 0:
        raise ValueError("Positive trial count required")
    b, s = continuum_mean(h, 1), math.expm1(4 * math.log1p(h)) / 4
    details = {"protocol_hash": config["protocol_hash"], "kind": "shell"} if "protocol_hash" in config else {}
    job, start = ledger.start("G1", details=details), time.perf_counter()
    free_h, free_w, accepted_h, accepted_w = [], [], [], []
    contacts = suppressed = rechecks = 0
    joint_counts={f'z{z:g}:u{u:g}':0 for z in (.25,.5,.75,1.) for u in (.25,.5,.75,1.)}
    joint_rechecks=[]
    counter = {"point_proposals": 0, "open_uniform_rejections": 0}
    try:
        for _ in range(n_histories):
            u, rejects = _uniform_open(rng, 1)
            counter["open_uniform_rejections"] += rejects
            nb = _positive_poisson(b, float(u[0]))
            nc = int(rng.poisson(s - b))
            points = np.concatenate((_restricted_points(rng, nb, h, True, b / s, counter),
                                     _restricted_points(rng, nc, h, False, 1 - b / s, counter)))
            trial = _evaluate_shell(points, h)
            flags,recheck=_free_joint_flags(points,h,trial)
            for key,flag in flags.items():joint_counts[key]+=int(flag)
            if recheck is not None:joint_rechecks.append({'history_index':len(free_h),**recheck})
            free_h.append(trial["free_arrival_delay"] / h)
            free_w.append(trial["free_warning_fraction"])
            suppressed += trial["suppressed_count"]
            rechecks += trial["precision_rechecks"]
            if not trial["right_censored"]:
                contacts += 1
                accepted_h.append(trial["arrival_delay"] / h)
                accepted_w.append(trial["accepted_warning_fraction"])
    except BaseException as exc:
        ledger.finish(job, time.perf_counter() - start, len(free_h), status="interrupted",
                      details=counter | {"exception": type(exc).__name__, "config": config})
        raise
    elapsed = time.perf_counter() - start
    resource_use = counter | {"job_id": job, "elapsed_seconds": elapsed, "history_evaluations": n_histories}
    ledger.finish(job, elapsed, n_histories, details=counter | {"config": config})
    return ShellSummary(n_histories, contacts, n_histories - contacts, b, s,
                        np.array(free_h), np.array(free_w), np.array(accepted_h), np.array(accepted_w),
                        resource_use, {"suppressed_points": suppressed, "precision_rechecks": rechecks,
                                       "free_joint_counts":joint_counts,"joint_endpoint_method":"analytic_identity",
                                       "free_joint_precision_rechecks":joint_rechecks,
                                       "phase": config.get("phase", "unspecified"),
                                       "accepted_warning": "first accepted signal to accepted arrival; only within horizon",
                                       "free_warning": "contacting free source's own warning"})


def shell_evidence(summary: ShellSummary, h: float) -> dict:
    """Small sufficient aggregates, retaining both free and accepted statistics."""
    joint = [{"z": z, "u": u,
              "count": shell_joint_count(summary,z,u),
              "exact_cdf": free_joint_cdf(h, z, u, 1)}
             for z in (.25, .5, .75, 1.) for u in (.25, .5, .75, 1.)]
    return {"h": h, "alpha": 1, "trials": summary.trials, "contact_count": summary.contact_count,
            "censored_count": summary.censored_count, "b": summary.b, "s": summary.s,
            "rigorous_probability_bounds": [summary.b * math.exp(-summary.s), -math.expm1(-summary.b)],
            "free_accepted_discrepancy_upper": summary.b * summary.s,
            "free_joint_counts": joint,
            "accepted_horizon_mean": float(np.mean(summary.accepted_horizon_fractions)) if summary.contact_count else None,
            "accepted_warning_mean": float(np.mean(summary.accepted_warning_fractions)) if summary.contact_count else None,
            "resource_use": summary.resource_use, "diagnostics": summary.diagnostics}
