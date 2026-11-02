from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_protocol_preserves_full_scientific_experiment():
    from seti_audit.contracts import load_protocol

    protocol = load_protocol(ROOT / "config/protocol.json")
    primary = [m for m in protocol.models if m.age_years == 10000]
    assert len(primary) == 16
    assert {(m.mu, m.speed_id) for m in primary} == {
        (mu, speed) for mu in (.1, 1, 3, 12) for speed in ("S1", "S2", "S3", "S4")
    }
    assert {(m.age_years, m.mu, m.speed_id) for m in protocol.models if m.age_years != 10000} == {
        (1000, 3, "S1"), (1000, 3, "S4"), (100000, 3, "S1"), (100000, 3, "S4")
    }
    assert protocol.thresholds == (.01, .05, .10)
    assert protocol.initial_checkpoints["primary_survivors"] == 100000
    assert protocol.extension_policy == {"multiplier": 2, "alpha_rule": "A/(M*j*(j+1))"}
    assert {d.detector_id: (d.pair_low, d.pair_high) for d in protocol.detectors} == {
        "Dnom": (.8836, .8836), "Dweak": (.44, .44), "Dhigh": (.94, .94),
        "Dpositive": (.44, .94), "Duncal": (0, 1),
    }
    for relative, digest in protocol.source_hashes.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("field,value", [("mu", -1), ("speed_id", "S9"), ("age_years", 0),
                                        ("model_id", True), ("model_id", 1.5), ("model_id", "1")])
def test_invalid_demographic_configuration_is_rejected(field, value):
    from seti_audit.contracts import ModelConfig

    with pytest.raises(ValueError):
        ModelConfig(**({"model_id": 1, "mu": 1, "age_years": 10000,
                       "speed_id": "S1", "future_multiplier": 1} | {field: value}))


def test_invalid_detector_interval_and_duplicate_models_are_rejected(tmp_path):
    from seti_audit.contracts import DetectorConfig, load_protocol

    with pytest.raises(ValueError):
        DetectorConfig("bad", .9, .2, False)
    raw = json.loads((ROOT / "config/protocol.json").read_text())
    raw["models"].append(raw["models"][0])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="duplicate"):
        load_protocol(bad)
