from dataclasses import replace

import pytest


def test_slow_projection_does_not_shrink_scientific_workload(repo_root):
    from seti_audit.contracts import load_protocol, WeightBounds
    from seti_audit.experiments import plan_precision

    protocol = load_protocol(repo_root / "config/protocol.json")
    result = plan_precision(protocol, {m.model_id: 1e6 for m in protocol.models},
                            {m.model_id: WeightBounds(.1, .2) for m in protocol.models})
    assert result.projected_seconds > 1e12
    assert all(result.initial_survivors[m.model_id] == (100000 if m.model_id < 16 else 25000)
               for m in protocol.models)
    assert len(result.initial_survivors) == 20
    assert any("optimiz" in r or "schedul" in r for r in result.execution_recommendations)


def test_tiny_calibration_and_pilot_preserve_protocol(repo_root, tmp_path):
    from seti_audit.artifacts import canonical_hash
    from seti_audit.contracts import load_protocol
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import calibrate, pilot
    from seti_audit.resources import ResourceLedger
    from dataclasses import asdict

    protocol = load_protocol(repo_root / "config/protocol.json")
    protocol = replace(protocol, models=(protocol.models[4], protocol.models[15]))
    before = canonical_hash(asdict(protocol))
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    ledger = ResourceLedger(tmp_path / "resources.jsonl")
    calibration = calibrate(protocol, catalog, schedule, ledger, sizes=(16, 33))
    result = pilot(protocol, catalog, schedule, ledger, n_histories=31)
    assert result.passed
    assert calibration.timings["records"]
    assert calibration.evidence_ids and result.evidence_ids
    assert canonical_hash(asdict(protocol)) == before
    assert ledger.usage()["history_evaluations"] > 0
    assert ledger.pending_jobs() == []


def test_development_cli_records_evidence(repo_root, tmp_path, monkeypatch):
    import json
    from seti_audit.artifacts import read_json_checked
    from seti_audit.cli import main

    raw = json.loads((repo_root / "config/protocol.json").read_text())
    raw["models"] = [m for m in raw["models"] if m["model_id"] in (4, 15)]
    config = tmp_path / "protocol.json"; config.write_text(json.dumps(raw))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/blueprint.md").write_bytes((repo_root / "docs/blueprint.md").read_bytes())
    monkeypatch.chdir(tmp_path)
    assert main(["calibrate", "--config", str(config), "--sizes", "16", "33"]) == 0
    assert main(["pilot", "--config", str(config), "--histories", "31"]) == 0
    assert read_json_checked(tmp_path / "results/calibration.json")["evidence_ids"]
    assert read_json_checked(tmp_path / "results/pilot.json")["passed"] is True


def test_empty_pilot_cannot_certify_mechanism_controls(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol
    from seti_audit.experiments import pilot
    from seti_audit.resources import ResourceLedger
    from seti_audit.data import load_catalog, load_schedule

    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    with pytest.raises(ValueError, match="positive|Positive"):
        pilot(protocol, catalog, schedule, ResourceLedger(tmp_path / "usage.jsonl"), n_histories=0)
