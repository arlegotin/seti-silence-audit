"""Retarded-time eligibility, linked source activity, and null-weight bounds."""

from collections import defaultdict
from itertools import combinations
import math

import numpy as np

from .contracts import DetectorConfig, EmissionConfig, Geometry, History, Schedule, WeightBounds

MASK_MHZ = ((1200, 1341.2), (1155.99, 1196.91), (1192.02, 1212.48),
            (1422.320, 1429.992), (1525, 1559), (1554.96, 1595.88), (1592.9525, 1610.485))


def frequency_admissible(track: tuple[float, float], duration_s: float) -> bool:
    frequency, drift = track
    if not all(math.isfinite(x) for x in (frequency, drift, duration_s)) or duration_s <= 0:
        raise ValueError("Invalid frequency track or integration duration")
    if drift == 0 or abs(drift) > 8.86:
        return False
    low, high = sorted((frequency, frequency + drift * duration_s / 1e6))
    return bool(low >= 1150 and high <= 1730
                and not any(low <= upper and high >= lower for lower, upper in MASK_MHZ))


def selection_eligible(track: tuple[float, float], duration_s: float,
                        on_hits: tuple[bool, bool], off_match: bool) -> bool:
    return bool(frequency_admissible(track, duration_s) and len(on_hits) == 2
                and all(on_hits) and not off_match)


def pair_recovery_bounds(eta: float) -> WeightBounds:
    if not 0 <= eta <= 1:
        raise ValueError("Per-ON recovery must be a probability")
    return WeightBounds(max(0., 2 * eta - 1), eta)


def joint_activity(windows: tuple[tuple[float, float], ...], on_fraction: float,
                    corr_years: float) -> float:
    if not 0 < on_fraction < 1 or not math.isfinite(corr_years) or corr_years <= 0:
        raise ValueError("Invalid stationary CTMC parameters")
    if not windows:
        return 1.0
    merged = []
    for start, end in sorted(windows):
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            raise ValueError("ON integration windows must have positive finite duration")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    off_rate = (1 - on_fraction) / corr_years
    log_probability = math.log(on_fraction) - off_rate * math.fsum(b - a for a, b in merged)
    for (_, previous_end), (next_start, _) in zip(merged, merged[1:]):
        p11 = on_fraction + (1 - on_fraction) * math.exp(-(next_start - previous_end) / corr_years)
        log_probability += math.log(p11)
    return math.exp(log_probability)


class _ReceivedInterval:
    def __init__(self, birth: float, radius: float, emission: EmissionConfig):
        self.birth, self.radius, self.emission = birth, radius, emission
        self.start = math.fsum((birth, radius, emission.delay_years))
        self.end = (math.inf if emission.lifetime_years is None else
                    math.fsum((birth, radius, emission.delay_years, emission.lifetime_years)))
        self.rechecks = []
        relevant = (birth, radius, emission.delay_years, emission.lifetime_years or 0)
        self.tolerance = max(1e-12, 64 * np.finfo(float).eps * max(1, *(abs(x) for x in relevant)))

    def _precise(self, mp):
        start = mp.mpf(self.birth) + mp.mpf(self.radius) + mp.mpf(self.emission.delay_years)
        end = mp.inf if self.emission.lifetime_years is None else start + mp.mpf(self.emission.lifetime_years)
        return start, end

    def contains(self, window: tuple[float, float]) -> bool:
        a, b = window
        ambiguous = abs(a - self.start) <= self.tolerance or abs(b - self.end) <= self.tolerance
        if not ambiguous:
            return self.start <= a and b <= self.end
        import mpmath as mp
        with mp.workdps(80):
            start, end = self._precise(mp)
            answer = bool(start <= mp.mpf(a) and mp.mpf(b) <= end)
            self.rechecks.append({"kind": "received_containment", "window": [a, b],
                                  "start_mp": str(start), "end_mp": str(end), "contains": answer})
            return answer

    def intersection_at_least(self, window: tuple[float, float], duration: float,
                               *, strictly_positive: bool = False) -> bool:
        a, b = window
        length = max(0., min(b, self.end) - max(a, self.start))
        if abs(length - duration) > self.tolerance:
            return length > duration if strictly_positive else length >= duration
        import mpmath as mp
        with mp.workdps(80):
            start, end = self._precise(mp)
            exact_length = max(mp.mpf(0), min(mp.mpf(b), end) - max(mp.mpf(a), start))
            answer = bool(exact_length > mp.mpf(duration) if strictly_positive else exact_length >= mp.mpf(duration))
            self.rechecks.append({"kind": "received_intersection", "window": [a, b],
                                  "length_mp": str(exact_length), "required_duration": duration,
                                  "strict": strictly_positive, "result": answer})
            return answer


def _union_null(zeta: float, detection_low: list[float], detection_high: list[float], rechecks) -> WeightBounds:
    minimum = max(detection_low, default=0.)
    maximum = min(1., math.fsum(detection_high))
    return WeightBounds(1 - zeta * maximum, 1 - zeta * minimum, tuple(rechecks))


def source_null_weight(birth_year: float, radius_ly: float, schedule: Schedule, site_id: str,
                        emission: EmissionConfig, detector: DetectorConfig,
                        visit_dependence: str = "nominal") -> WeightBounds:
    if emission.zeta == 0 or birth_year == math.inf:
        return WeightBounds(1., 1.)
    if visit_dependence not in {"nominal", "robust"}:
        raise ValueError("Unknown repeated-visit dependence model")
    if schedule.schedule_grade == "unavailable":
        raise ValueError("Unavailable schedule cannot establish an empirical likelihood")
    received = _ReceivedInterval(birth_year, radius_ly, emission)
    if schedule.schedule_grade == "coarsened_F1":
        visits = [v for v in schedule.bounded_visits if v.site_id == site_id]
        detection_low, detection_high = [], []
        for visit in visits:
            if detector.allow_partial:
                possible = any(received.intersection_at_least(o, 0., strictly_positive=True)
                               for o in visit.allowed_intervals)
                detection_low.append(0.)
                detection_high.append(1. if possible else 0.)
                continue
            certain = all(received.contains(o) for o in visit.allowed_intervals)
            possible = any(received.intersection_at_least(o, 2 * visit.duration_year)
                           for o in visit.allowed_intervals)
            if emission.activity == "ctmc":
                f = emission.on_fraction
                off_rate = (1 - f) / (emission.corr_days / 365.25)
                survival = math.exp(-off_rate * 2 * visit.duration_year)
                activity_low, activity_high = f * f * survival, f * survival
            else:
                activity_low = activity_high = 1.
            detection_low.append(detector.pair_low * activity_low if certain else 0.)
            detection_high.append(detector.pair_high * activity_high if possible else 0.)
        return _union_null(emission.zeta, detection_low, detection_high, received.rechecks)
    by_visit = defaultdict(list)
    for scan in schedule.exact_scans:
        if scan.site_id == site_id:
            by_visit[scan.visit_id].append((scan.start_year, math.fsum((scan.start_year, scan.duration_year))))
    windows = list(by_visit.values())
    if any(len(w) != 2 for w in windows):
        raise ValueError("A fully specified visit must have both ON integrations")
    if not windows:
        return WeightBounds(1., 1.)
    if detector.allow_partial:
        high = [1. if any(received.intersection_at_least(o, 0., strictly_positive=True) for o in pair) else 0.
                for pair in windows]
        return _union_null(emission.zeta, [0.] * len(high), high, received.rechecks)
    full = [all(received.contains(o) for o in pair) for pair in windows]
    cached_activity = {}

    def activity(subset):
        key = tuple(subset)
        if key not in cached_activity:
            if not all(full[i] for i in key):
                result = 0.
            elif emission.activity == "ctmc":
                result = joint_activity(tuple(window for i in key for window in windows[i]),
                                        emission.on_fraction, emission.corr_days / 365.25)
            else:
                result = 1.
            cached_activity[key] = result
        return cached_activity[key]

    if visit_dependence == "robust":
        marginal_activity = [activity((i,)) for i in range(len(windows))]
        return _union_null(emission.zeta, [detector.pair_low * g for g in marginal_activity],
                           [detector.pair_high * g for g in marginal_activity], received.rechecks)

    def point(p):
        if emission.activity == "always":
            nondetection = (1 - p)**sum(full)
            return 1 - emission.zeta * (1 - nondetection)
        terms = []
        for size in range(1, len(windows) + 1):
            for subset in combinations(range(len(windows)), size):
                terms.append((-1)**(size + 1) * activity(subset) * p**size)
        return 1 - emission.zeta * math.fsum(terms)

    low = point(detector.pair_high)
    high = low if detector.pair_low == detector.pair_high else point(detector.pair_low)
    return WeightBounds(low, high, tuple(received.rechecks))


def null_weight(history: History, geometry: Geometry, schedule: Schedule,
                  emission: EmissionConfig, detector: DetectorConfig,
                  visit_dependence: str = "nominal") -> WeightBounds:
    weights = [source_null_weight(float(history.birth_years[i]), float(geometry.radii_ly[i]),
                                   schedule, geometry.site_ids[i], emission, detector, visit_dependence)
               for i in history.accepted_indices]

    def product(endpoint):
        values = [getattr(weight, endpoint) for weight in weights]
        return 0. if any(value == 0 for value in values) else math.exp(math.fsum(math.log(value) for value in values))

    return WeightBounds(product("low"), product("high"),
                        tuple(event for weight in weights for event in weight.rechecks))


def batch_null_weights(batch, geometry, schedule, emission, detector, visit_dependence="nominal"):
    """Vectorized F1 response, with scalar precision fallback at boundaries."""
    count = len(batch.arrival_years)
    if emission.zeta == 0:
        return np.ones(count), np.ones(count), {"source_precision_rechecks": 0}
    if schedule.schedule_grade != "coarsened_F1":
        from .model import history_at
        weights = [null_weight(history_at(batch, i), geometry, schedule, emission, detector, visit_dependence)
                   for i in range(count)]
        return (np.array([w.low for w in weights]), np.array([w.high for w in weights]),
                {"scalar_histories": count, "source_precision_rechecks": sum(len(w.rechecks) for w in weights)})
    if visit_dependence not in {"nominal", "robust"}:
        raise ValueError("Unknown repeated-visit dependence model")
    by_site = defaultdict(list)
    for visit in schedule.bounded_visits:
        by_site[visit.site_id].append(visit)
    log_low, log_high = np.zeros(count), np.zeros(count)
    zero_low, zero_high = np.zeros(count, dtype=bool), np.zeros(count, dtype=bool)
    rechecks = 0
    for index, site_id in enumerate(geometry.site_ids):
        rows = np.flatnonzero(batch.accepted_mask[:, index])
        if not len(rows) or not by_site[site_id]:
            continue
        birth, radius = batch.birth_years[rows, index], float(geometry.radii_ly[index])
        start = birth + radius + emission.delay_years
        end = np.full(len(rows), np.inf) if emission.lifetime_years is None else start + emission.lifetime_years
        tolerance = np.maximum(1e-12, 64 * np.finfo(float).eps * np.maximum.reduce(
            (np.ones(len(rows)), np.abs(birth), np.full(len(rows), max(radius, emission.delay_years, emission.lifetime_years or 0.)))))
        uncertain = np.zeros(len(rows), dtype=bool)
        maximum, minimum = np.zeros(len(rows)), np.zeros(len(rows))
        for visit in by_site[site_id]:
            certain, possible = np.ones(len(rows), dtype=bool), np.zeros(len(rows), dtype=bool)
            for a, b in visit.allowed_intervals:
                certain &= (start <= a) & (end >= b)
                length = np.minimum(end, b) - np.maximum(start, a)
                target = 0. if detector.allow_partial else 2 * visit.duration_year
                possible |= length > 0 if detector.allow_partial else length >= target
                uncertain |= (np.abs(start - a) <= tolerance) | (np.abs(end - b) <= tolerance) | (np.abs(length - target) <= tolerance)
            if detector.allow_partial:
                low_d, high_d = np.zeros(len(rows)), possible.astype(float)
            else:
                if emission.activity == "ctmc":
                    f = emission.on_fraction
                    survival = math.exp(-(1 - f) / (emission.corr_days / 365.25) * 2 * visit.duration_year)
                    a_low, a_high = f * f * survival, f * survival
                else:
                    a_low = a_high = 1.
                low_d = certain * detector.pair_low * a_low
                high_d = possible * detector.pair_high * a_high
            maximum += high_d
            minimum = np.maximum(minimum, low_d)
        lower = 1 - emission.zeta * np.minimum(1., maximum)
        upper = 1 - emission.zeta * minimum
        for j in np.flatnonzero(uncertain):
            exact = source_null_weight(float(birth[j]), radius, schedule, site_id, emission, detector, visit_dependence)
            lower[j], upper[j] = exact.low, exact.high
            rechecks += 1
        zero_low[rows] |= lower == 0
        zero_high[rows] |= upper == 0
        log_low[rows] += np.log(np.where(lower > 0, lower, 1.))
        log_high[rows] += np.log(np.where(upper > 0, upper, 1.))
    low, high = np.exp(log_low), np.exp(log_high)
    low[zero_low], high[zero_high] = 0., 0.
    return low, high, {"source_precision_rechecks": rechecks}
