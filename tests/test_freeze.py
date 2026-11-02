from dataclasses import replace
from pathlib import Path

import pytest


@pytest.fixture
def small_protocol(repo_root):
    from seti_audit.contracts import load_protocol

    protocol = load_protocol(repo_root / "config/protocol.json")
    return replace(protocol, purpose="smoke", models=(protocol.models[0],),
                   initial_checkpoints={key: 8 for key in protocol.initial_checkpoints})


@pytest.fixture
def frozen_smoke(repo_root, tmp_path, small_protocol):
    from seti_audit.contracts import CalibrationResult, PilotResult, WeightBounds
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import freeze_protocol

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    calibration = CalibrationResult({0: 8}, {}, 4, 1., {0: .01}, {0: WeightBounds(1., 1.)},
                                    {"identity": {"phase": "development"}}, 1000, (), ("synthetic-smoke-G2",))
    pilot = PilotResult(True, ("synthetic-smoke-G3",), {"scope": "smoke"}, {})
    return freeze_protocol(small_protocol, catalog, schedule, calibration, pilot, tmp_path / "results")


def test_smoke_freeze_is_hash_bound_immutable_and_explicitly_synthetic(frozen_smoke):
    from seti_audit.experiments import verify_protocol_lock
    from seti_audit.artifacts import read_json_checked

    lock = frozen_smoke
    assert lock["purpose"] == "smoke"
    assert verify_protocol_lock(lock)
    root = Path(lock["_output_dir"])
    assert read_json_checked(root / "matrix.json", lock["matrix_sha256"])["cells"] == lock["cells"]
    changed = dict(lock, thresholds=[.5])
    with pytest.raises(ValueError, match="hash"):
        verify_protocol_lock(changed)


def test_research_freeze_rejects_retuned_grid_before_simulation(repo_root, tmp_path, small_protocol):
    from seti_audit.experiments import freeze_protocol
    from seti_audit.data import load_catalog, load_schedule

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    with pytest.raises(ValueError, match="scientific grid"):
        freeze_protocol(replace(small_protocol, purpose="research"), catalog, schedule, None, None, tmp_path / "results")


def test_resume_rejects_changed_dependency_identity(frozen_smoke, monkeypatch):
    import seti_audit.experiments as experiments

    monkeypatch.setattr(experiments, "execution_identity", lambda: {"python": "changed"})
    with pytest.raises(ValueError, match="identity"):
        experiments.verify_protocol_lock(frozen_smoke)
