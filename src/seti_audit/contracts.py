"""Scientific configuration contracts shared across validated components."""

from dataclasses import dataclass, field
import math
from numbers import Integral
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .artifacts import read_json_checked

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class ModelConfig:
    model_id: int
    mu: float
    age_years: float
    speed_id: str
    future_multiplier: float = 1.0

    def __post_init__(self):
        if (not math.isfinite(self.mu) or self.mu < 0
                or not math.isfinite(self.age_years) or self.age_years <= 0
                or not math.isfinite(self.future_multiplier) or self.future_multiplier < 0
                or self.speed_id not in {"S1", "S2", "S3", "S4"}):
            raise ValueError("Invalid demographic configuration")


@dataclass(frozen=True)
class EmissionConfig:
    emission_id: str
    zeta: float
    delay_years: float
    lifetime_years: float | None
    activity: str
    on_fraction: float = .1
    corr_days: float = 1.0

    def __post_init__(self):
        if (not 0 <= self.zeta <= 1 or not math.isfinite(self.delay_years)
                or self.delay_years < 0 or self.activity not in {"always", "ctmc"}
                or not 0 < self.on_fraction < 1
                or not math.isfinite(self.corr_days) or self.corr_days <= 0
                or (self.lifetime_years is not None and
                    (not math.isfinite(self.lifetime_years) or self.lifetime_years <= 0))):
            raise ValueError("Invalid emission configuration")


@dataclass(frozen=True)
class DetectorConfig:
    detector_id: str
    pair_low: float
    pair_high: float
    allow_partial: bool = False

    def __post_init__(self):
        if not 0 <= self.pair_low <= self.pair_high <= 1:
            raise ValueError("Invalid detector probability interval")


@dataclass(frozen=True)
class Protocol:
    schema_version: int
    horizon_years: float
    models: tuple[ModelConfig, ...]
    emissions: tuple[EmissionConfig, ...]
    detectors: tuple[DetectorConfig, ...]
    thresholds: tuple[float, ...]
    future_multipliers: tuple[float, ...]
    initial_checkpoints: dict[str, int]
    extension_policy: dict
    seed_roots: dict
    error_pools: dict[str, float]
    tolerances: dict[str, float]
    source_hashes: dict[str, str]


@dataclass(frozen=True)
class Geometry:
    site_ids: tuple[str, ...]
    xyz_ly: FloatArray
    radii_ly: FloatArray
    distances_ly: FloatArray

    def __post_init__(self):
        n = len(self.site_ids)
        if len(set(self.site_ids)) != n:
            raise ValueError("Duplicate physical site IDs")
        for name, shape in [("xyz_ly", (n, 3)), ("radii_ly", (n,)), ("distances_ly", (n, n))]:
            value = np.array(getattr(self, name), dtype=np.float64, copy=True)
            if value.shape != shape or not np.all(np.isfinite(value)):
                raise ValueError(f"Invalid geometry {name}")
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        if np.any(self.radii_ly < 0) or np.any(self.distances_ly < 0):
            raise ValueError("Negative geometry distance")


@dataclass(frozen=True)
class Catalog:
    source_rows: tuple[dict, ...]
    geometry: Geometry
    provenance: dict


@dataclass(frozen=True)
class Scan:
    visit_id: str
    site_id: str
    scan_index: int
    start_year: float
    duration_year: float
    paired_visit_id: str
    source_row: str | None = None
    session_date: str | None = None
    start_mjd: float | None = None
    source_file: str | None = None


@dataclass(frozen=True)
class BoundedVisit:
    visit_id: str
    site_id: str
    allowed_intervals: tuple[tuple[float, float], ...]
    duration_year: float
    source_row: str | None = None
    year_group: str | None = None


@dataclass(frozen=True)
class Schedule:
    exact_scans: tuple[Scan, ...]
    bounded_visits: tuple[BoundedVisit, ...]
    schedule_grade: str
    detector_grade: str
    endpoint: dict
    provenance: dict

    def __post_init__(self):
        if self.schedule_grade not in {"exact", "coarsened_F1", "unavailable"}:
            raise ValueError("Unknown schedule grade")
        if self.detector_grade not in {"assumed_F2", "unconstrained_F2", "calibrated"}:
            raise ValueError("Unknown detector grade")
        if self.exact_scans and self.bounded_visits:
            raise ValueError("Schedule mixes exact and interval representations")
        if self.schedule_grade == "exact" and self.bounded_visits:
            raise ValueError("Interval visits cannot be graded exact")
        if self.schedule_grade == "coarsened_F1" and self.exact_scans:
            raise ValueError("Coarsened schedule cannot contain imputed exact scans")


@dataclass(frozen=True)
class FirstClocks:
    birth_years: FloatArray
    speeds: FloatArray
    speed_gaps: FloatArray
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        shape = np.asarray(self.birth_years).shape
        if len(shape) != 1:
            raise ValueError("First clocks must be site-indexed vectors")
        for name in ("birth_years", "speeds", "speed_gaps"):
            value = np.array(getattr(self, name), dtype=np.float64, copy=True)
            if value.shape != shape:
                raise ValueError("First-clock array shapes disagree")
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        if np.any(np.isnan(self.birth_years) | np.isneginf(self.birth_years)):
            raise ValueError("Birth clocks allow only finite values or positive infinity")
        if (np.any(~np.isfinite(self.speeds)) or np.any((self.speeds <= 0) | (self.speeds >= 1))
                or np.any(~np.isfinite(self.speed_gaps)) or np.any(self.speed_gaps <= 0)):
            raise ValueError("Speed marks must be strictly subluminal with positive finite q")
        if not np.allclose(self.speeds, 1 / (1 + self.speed_gaps), rtol=4 * np.finfo(float).eps, atol=0):
            raise ValueError("Inconsistent speed and speed-gap marks")


@dataclass(frozen=True)
class History:
    accepted_indices: IntArray
    birth_years: FloatArray
    speeds: FloatArray
    speed_gaps: FloatArray
    occupation_years: FloatArray
    arrival_year: float
    right_censored: bool
    diagnostics: dict

    @property
    def survives(self) -> bool:
        return bool(self.diagnostics.get("survives", self.arrival_year > 0))

    @property
    def arrives_within_horizon(self) -> bool:
        return bool(self.diagnostics.get("arrives_within_horizon", 0 < self.arrival_year <= 100))


@dataclass(frozen=True)
class FutureMarks:
    residual_hazards: FloatArray
    speeds: FloatArray
    speed_gaps: FloatArray
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        residual = np.array(self.residual_hazards, dtype=np.float64, copy=True)
        if residual.ndim != 1 or np.any(np.isnan(residual) | (residual <= 0)):
            raise ValueError("Future hazards must be positive or infinity for an ineligible site")
        checked = FirstClocks(np.full(residual.shape, np.inf), self.speeds, self.speed_gaps)
        if checked.speeds.shape != residual.shape:
            raise ValueError("Future-mark shape mismatch")
        residual.setflags(write=False)
        object.__setattr__(self, "residual_hazards", residual)
        object.__setattr__(self, "speeds", checked.speeds)
        object.__setattr__(self, "speed_gaps", checked.speed_gaps)


@dataclass(frozen=True)
class WeightBounds:
    low: float
    high: float
    rechecks: tuple[dict, ...] = field(default=(), compare=False, repr=False)

    def __post_init__(self):
        if not (math.isfinite(self.low) and math.isfinite(self.high)
                and 0 <= self.low <= self.high <= 1):
            raise ValueError(f"Invalid probability bounds: [{self.low},{self.high}]")


@dataclass(frozen=True)
class OracleResult:
    C: float
    likelihood: WeightBounds
    R0: WeightBounds
    R: WeightBounds
    absolute_errors: dict
    joint_bounds: dict
    validation: dict = field(default_factory=dict)
    status: str = "validated"


@dataclass(frozen=True)
class ShellSummary:
    trials: int
    contact_count: int
    censored_count: int
    b: float
    s: float
    free_horizon_fractions: FloatArray
    free_warning_fractions: FloatArray
    accepted_horizon_fractions: FloatArray
    accepted_warning_fractions: FloatArray
    resource_use: dict
    diagnostics: dict


@dataclass(frozen=True)
class AuditCounts:
    histories: int
    arrivals: int
    nulls: int
    arrival_nulls: int
    sum_w: float
    sum_bw: float
    bound_counts: dict[str, int]
    bound_sums: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        values = (self.histories, self.arrivals, self.nulls, self.arrival_nulls)
        if (any(not isinstance(x, Integral) or isinstance(x, bool) or x < 0 for x in values)
                or self.arrivals > self.histories or self.nulls > self.histories
                or self.arrival_nulls > min(self.arrivals, self.nulls)
                or self.nulls - self.arrival_nulls > self.histories - self.arrivals
                or not math.isfinite(self.sum_w) or not math.isfinite(self.sum_bw)
                or not 0 <= self.sum_bw <= self.sum_w <= self.histories):
            raise ValueError("Inconsistent audit counts/sums")
        if self.bound_counts:
            keys = {"null_low", "null_high", "J_low", "J_high", "K_low", "K_high"}
            if (set(self.bound_counts) != keys or set(self.bound_sums) != keys
                    or any(not isinstance(x, Integral) or isinstance(x, bool) or not 0 <= x <= self.histories
                           for x in self.bound_counts.values())
                    or any(not math.isfinite(x) or not 0 <= x <= self.histories for x in self.bound_sums.values())):
                raise ValueError("Invalid interval-weight audit components")
            for suffix in ("low", "high"):
                if self.bound_counts[f"J_{suffix}"] + self.bound_counts[f"K_{suffix}"] != self.bound_counts[f"null_{suffix}"]:
                    raise ValueError("Audit components do not partition nulls")
                if (self.bound_counts[f"J_{suffix}"] > self.arrivals
                        or self.bound_counts[f"K_{suffix}"] > self.histories - self.arrivals
                        or self.bound_sums[f"J_{suffix}"] > self.arrivals
                        or self.bound_sums[f"K_{suffix}"] > self.histories - self.arrivals):
                    raise ValueError("Audit component exceeds its arrival partition")
            if any(self.bound_counts[f"{q}_low"] > self.bound_counts[f"{q}_high"] for q in ("null", "J", "K")):
                raise ValueError("Non-nested audit bounds")


@dataclass(frozen=True)
class Summary:
    rows: tuple[dict, ...]
    certified: dict
    possible: dict
    envelopes: dict
    certificates: dict
    interval_evidence: dict


@dataclass(frozen=True)
class ClockBatch:
    birth_years: FloatArray
    speeds: FloatArray
    speed_gaps: FloatArray
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        arrays = [np.asarray(getattr(self, name), dtype=float) for name in ("birth_years", "speeds", "speed_gaps")]
        shape = arrays[0].shape
        if len(shape) != 2 or any(a.shape != shape for a in arrays):
            raise ValueError("Batch clocks must share (history,site) shape")
        checked = FirstClocks(*(a.ravel() for a in arrays))
        for name in ("birth_years", "speeds", "speed_gaps"):
            object.__setattr__(self, name, getattr(checked, name).reshape(shape))


@dataclass(frozen=True)
class HistoryBatch:
    birth_years: FloatArray
    speeds: FloatArray
    speed_gaps: FloatArray
    candidate_order: IntArray
    accepted_mask: NDArray[np.bool_]
    occupation_years: FloatArray
    arrival_years: FloatArray
    right_censored: NDArray[np.bool_]
    survives: NDArray[np.bool_]
    arrives_within_horizon: NDArray[np.bool_]
    diagnostics: dict


@dataclass(frozen=True)
class CalibrationResult:
    initial_survivors: dict[int, int]
    initial_diagnostic_proposals: dict[int, int]
    logical_batch_size: int
    projected_seconds: float
    proposal_costs: dict[int, float]
    acceptance_bounds: dict[int, WeightBounds]
    timings: dict
    rss_bytes: int
    execution_recommendations: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class PilotResult:
    passed: bool
    evidence_ids: tuple[str, ...]
    controls: dict
    diagnostics: dict


def load_protocol(path: Path) -> Protocol:
    raw = read_json_checked(path)
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported protocol schema_version")
    models = tuple(ModelConfig(**value) for value in raw["models"])
    emissions = tuple(EmissionConfig(**value) for value in raw["emissions"])
    detectors = tuple(DetectorConfig(**value) for value in raw["detectors"])
    for label, identifiers in [
        ("model", [m.model_id for m in models]),
        ("emission", [e.emission_id for e in emissions]),
        ("detector", [d.detector_id for d in detectors]),
    ]:
        if len(set(identifiers)) != len(identifiers):
            raise ValueError(f"duplicate {label} IDs")
    thresholds = tuple(raw["thresholds"])
    if not thresholds or any(not 0 < t < 1 for t in thresholds):
        raise ValueError("Invalid compatibility thresholds")
    if any(not isinstance(n, int) or n <= 0 for n in raw["initial_checkpoints"].values()):
        raise ValueError("Initial checkpoints must be positive integers")
    if raw["extension_policy"] != {"multiplier": 2, "alpha_rule": "A/(M*j*(j+1))"}:
        raise ValueError("Unsupported checkpoint extension policy")
    if any(not 0 < a < 1 for a in raw["error_pools"].values()) or sum(raw["error_pools"].values()) > .05:
        raise ValueError("Invalid familywise error allocation")
    return Protocol(
        schema_version=1, horizon_years=raw["horizon_years"], models=models,
        emissions=emissions, detectors=detectors, thresholds=thresholds,
        future_multipliers=tuple(raw["future_multipliers"]),
        initial_checkpoints=raw["initial_checkpoints"], extension_policy=raw["extension_policy"],
        seed_roots=raw["seed_roots"], error_pools=raw["error_pools"],
        tolerances=raw["tolerances"], source_hashes=raw["source_hashes"],
    )
