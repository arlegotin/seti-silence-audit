"""Scientific configuration contracts shared across validated components."""

from dataclasses import dataclass
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
