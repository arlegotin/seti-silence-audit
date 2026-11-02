from dataclasses import replace
from pathlib import Path

import pytest


@pytest.fixture
def small_protocol(repo_root, request):
    from seti_audit.contracts import load_protocol

    protocol = load_protocol(repo_root / "config/protocol.json")
    model_id = getattr(request, "param", 0)
    return replace(protocol, purpose="smoke", models=(protocol.models[model_id],),
                   initial_checkpoints={key: 8 for key in protocol.initial_checkpoints})


@pytest.fixture
def frozen_smoke(repo_root, tmp_path, small_protocol):
    from seti_audit.contracts import CalibrationResult, PilotResult, WeightBounds
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import freeze_protocol

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    model = small_protocol.models[0]
    mid = model.model_id
    calibration = CalibrationResult({mid: 8}, {mid: 8} if model.speed_id in ("S3", "S4") else {}, 4, 1., {mid: .01}, {mid: WeightBounds(.1, 1.)},
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


def test_changed_source_bytes_block_resume(frozen_smoke, tmp_path, monkeypatch):
    from seti_audit.experiments import verify_protocol_lock

    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/blueprint.md").write_bytes(b"changed source")
    with pytest.raises(ValueError, match="[Ss]ource hash"):
        verify_protocol_lock(frozen_smoke)


def test_cost_only_reduction_in_initial_precision_is_rejected(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol, CalibrationResult, PilotResult, WeightBounds
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import freeze_protocol

    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    calibration = CalibrationResult({m.model_id: 25000 for m in protocol.models},
                                    {m.model_id: 50000 for m in protocol.models if m.speed_id in ("S3", "S4")},
                                    1024, 1e12, {}, {m.model_id: WeightBounds(.1, 1.) for m in protocol.models},
                                    {}, 1000, (), ("evidence",))
    with pytest.raises(ValueError, match="precision"):
        freeze_protocol(protocol, catalog, schedule, calibration, PilotResult(True, ("evidence",), {}, {}), tmp_path / "results")


def test_selected_tests_cannot_supply_research_correctness_evidence(repo_root, tmp_path, monkeypatch):
    import hashlib
    from seti_audit.contracts import load_protocol, PilotResult, WeightBounds
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import freeze_protocol, plan_precision, _identity
    from seti_audit.artifacts import write_json_atomic

    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    calibration = plan_precision(protocol, {m.model_id: .1 for m in protocol.models}, {m.model_id: WeightBounds(1., 1.) for m in protocol.models})
    identity = _identity(protocol, catalog, schedule)
    calibration = replace(calibration, timings={"identity": identity}, evidence_ids=("fixture",))
    pilot = PilotResult(True, ("fixture",), {}, {"identity": identity})
    source = repo_root / "src/seti_audit/model.py"
    write_json_atomic(tmp_path / "results/correctness.json", {"status": "passed", "scope": "selected", "test_count": 1,
                                                             "component_hashes": {str(source): hashlib.sha256(source.read_bytes()).hexdigest()}})
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ArithmeticError, match="full correctness"):
        freeze_protocol(protocol, catalog, schedule, calibration, pilot, tmp_path / "results")
