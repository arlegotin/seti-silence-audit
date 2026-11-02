"""Scientific configuration contracts shared across validated components."""

from dataclasses import dataclass, field
import math
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
