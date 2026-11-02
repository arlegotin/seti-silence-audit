import csv
import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def report_project(repo_root, tmp_path):
    from seti_audit.artifacts import canonical_hash, write_json_atomic

    def make(case="complete"):
        bundle = json.loads((repo_root / f"tests/fixtures/report_{case}.json").read_text())
        root = tmp_path / case / "results"; root.mkdir(parents=True)
        cells = [cell | {"model_kind": "interacting", "baseline_id": cell["cell_id"], "future_multiplier": 1.,
                         "emission_id": "E1", "detector_id": "Dnom", "schedule_grade": bundle["schedule_grade"],
                         "detector_grade": bundle["detector_grade"], "interval_ids": {}, "thresholds": [.01, .05, .1]}
                 for cell in bundle["cells"]]
        registry = {"items": {}, "pools": {"primary": {"A": .025, "M": 0}, "diagnostics": {"A": .025, "M": 0}}}
        body = {"purpose": bundle["purpose"], "cells": cells, "thresholds": [.01, .05, .1], "bound_registry": registry,
                "matrix_sha256": canonical_hash({"cells": cells}), "registry_sha256": canonical_hash(registry),
                "config": {"source_hashes": {}, "models": []},
                "catalog_provenance": {"source_status": "synthetic_control", "physical_sites": 2, "source_rows": 2},
                "schedule": {"schedule_grade": bundle["schedule_grade"], "detector_grade": bundle["detector_grade"],
                             "endpoint": {"t0_interval_utc": ["2023-05-13T00:00:00Z", "2023-05-15T00:00:00Z"]}}}
        lock = body | {"protocol_hash": canonical_hash(body)}
        write_json_atomic(root / "protocol.lock.json", lock)
        write_json_atomic(root / "matrix.json", {"cells": cells}); write_json_atomic(root / "bound_registry.json", registry)
        rows = [cell | {"protocol_hash": lock["protocol_hash"], "intervals": bundle["rows"][cell["cell_id"]],
                        "estimates": {"C": None, "likelihood": None, "R0": None, "R": None},
                        "numerical_errors": {}, "completion_status": "validated_synthetic", "counts": None}
                for cell in cells if cell["cell_id"] in bundle["rows"]]
        result = {"status": "smoke_complete", "protocol_hash": lock["protocol_hash"], "summary": {"rows": rows, "interval_evidence": {}},
                  "looks": {}, "reference_checks": [], "batch_hashes": [], "batches": []}
        result["content_hash"] = canonical_hash(result)
        write_json_atomic(root / "confirmation.json", result)
        if bundle["theorem_status"] != "unperformed":
            write_json_atomic(root / "theorem/deterministic.json", {"status": bundle["theorem_status"], "scope": "synthetic fixture"})
        return root, tmp_path / case / "report"
    return make


def test_regeneration_is_saved_evidence_only_and_preserves_scoped_schema(report_project, monkeypatch):
    import numpy as np
    import seti_audit.acquisition as acquisition
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked

    def forbidden(*args, **kwargs):
        raise AssertionError("Report regeneration cannot acquire or simulate")
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(acquisition, "fetch_public", forbidden)
    root, output = report_project()
    first = render_report(root, output)
    tables = (root / "tables/model_rows.csv").read_bytes()
    conclusions = (root / "conclusions.json").read_bytes()
    second = render_report(root, output)
    assert (root / "tables/model_rows.csv").read_bytes() == tables
    assert (root / "conclusions.json").read_bytes() == conclusions
    assert "synthetic" in (output / "REPORT.md").read_text().lower()
    required = {"cell_id", "family_ids", "model_kind", "model_id", "k", "C", "likelihood", "R0", "R", "intervals",
                "numerical_errors", "compatibility", "attempted", "surviving", "nulls", "arrivals", "checkpoint_ids",
                "completion_status", "failure_ids", "evidence_ids", "protocol_hash", "schedule_grade", "detector_grade"}
    with (root / "tables/model_rows.csv").open() as stream:
        assert required <= set(csv.DictReader(stream).fieldnames)
    registry = read_json_checked(root / "evidence.json")["evidence"]
    for claim in read_json_checked(root / "conclusions.json")["claims"]:
        assert all(eid in registry for eid in claim["evidence_ids"])
    for artifact in second["artifacts"].values():
        path = Path(artifact["path"])
        assert path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    assert set(first["figures"]) == {"family_envelopes", "likelihood_risk", "ideal_discrepancy", "theorem_ratios"}


def test_missing_mandatory_cell_remains_in_outer_envelope_and_blocks_positive(report_project):
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked

    root, output = report_project("blocked")
    render_report(root, output)
    rows = read_json_checked(root / "model_rows.json")["rows"]
    missing = next(r for r in rows if r["cell_id"] == "missing")
    assert missing["completion_status"] == "pending"
    assert missing["intervals"]["R"] == [0., 1.]
    family = read_json_checked(root / "family_envelopes.json")["envelopes"]["interacting/primary"]["0.05"]
    assert family["Ipost"] == [0., 1.]
    claims = read_json_checked(root / "conclusions.json")["claims"]
    assert next(c for c in claims if c["claim_id"] == "family:interacting/primary")["outcome_category"] is None
    assert "assumed_F2" in (output / "REPORT.md").read_text()


def test_fully_excluded_family_has_no_conditional_risk(report_project):
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked

    root, output = report_project()
    render_report(root, output)
    family = read_json_checked(root / "family_envelopes.json")["envelopes"]["excluded_only"]["0.05"]
    assert family["Ipost"] is None
    claims = read_json_checked(root / "conclusions.json")["claims"]
    assert next(c for c in claims if c["claim_id"] == "family:excluded_only")["decision"] == "incompatible"


def test_report_cli_validates_the_requested_protocol_instead_of_a_neighbor(report_project):
    from seti_audit.artifacts import write_json_atomic
    from seti_audit.cli import main

    root, output = report_project()
    write_json_atomic(root / "other-protocol.json", {"not_the_protocol": True})
    assert main(["report", "--protocol", str(root / "other-protocol.json"), "--out", str(output), "--from-results"]) == 2


def test_invalid_theorem_does_not_erase_independent_finite_site_result(report_project):
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked

    root, output = report_project("invalid")
    render_report(root, output)
    claims = read_json_checked(root / "conclusions.json")["claims"]
    assert next(c for c in claims if c["claim_id"] == "continuum_reference")["outcome_category"] == "invalid experiment"
    assert next(c for c in claims if c["claim_id"] == "family:interacting/primary")["outcome_category"] == "supported contribution"


@pytest.mark.parametrize("category", ["supported contribution", "informative negative result", "practical infeasibility", "inconclusive evidence", "invalid experiment"])
def test_saved_scoped_claims_resolve_to_evidence(report_project, category):
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import write_json_atomic, read_json_checked

    root, output = report_project()
    claim = {"claim_id": "synthetic-extra", "claim": "Synthetic category rendering control", "outcome_category": category,
             "scope": "synthetic fixture", "evidence_ids": ["confirmation"], "unresolved_dependencies": [],
             "basis": {"measured_requirement_bytes": 100, "available_bytes": 50, "attempted_remedies": ["streamed input", "smaller batch"]}}
    write_json_atomic(root / "claims.json", {"claims": [claim]})
    render_report(root, output)
    assert next(c for c in read_json_checked(root / "conclusions.json")["claims"] if c["claim_id"] == "synthetic-extra")["outcome_category"] == category


def test_pre_freeze_evidence_report_does_not_invent_a_protocol(tmp_path):
    from seti_audit.artifacts import write_json_atomic, read_json_checked
    from seti_audit.reporting import render_report

    root = tmp_path / "results"; root.mkdir()
    configuration = root / "configuration.json"
    write_json_atomic(configuration, {"purpose": "synthetic reporting control"})
    status = {"stage": "pre_freeze", "purpose": "smoke", "schedule_grade": "unavailable", "detector_grade": "unconstrained_F2",
              "evidence": {"configuration": {"path": "configuration.json", "sha256": hashlib.sha256(configuration.read_bytes()).hexdigest()}},
              "claims": [{"claim_id": "source_access", "claim": "Synthetic blocked-input reporting control", "scope": "synthetic fixture",
                          "outcome_category": "inconclusive evidence", "evidence_ids": ["configuration"],
                          "unresolved_dependencies": ["source-backed observing log"]}]}
    write_json_atomic(root / "evidence_status.json", status)
    render_report(root, tmp_path / "report")
    assert not (root / "protocol.lock.json").exists()
    assert read_json_checked(root / "conclusions.json")["protocol_hash"] is None
    assert "not frozen" in (tmp_path / "report/REPORT.md").read_text().lower()
    from seti_audit.cli import main
    assert main(["report", "--evidence", str(root / "evidence_status.json"), "--out", str(tmp_path / "report-cli"), "--from-results"]) == 0


def test_all_four_static_figure_families_are_exported_from_saved_values(report_project, monkeypatch):
    from copy import deepcopy
    import struct
    import numpy as np
    from seti_audit.artifacts import canonical_hash, read_json_checked, write_json_atomic
    from seti_audit.reporting import render_report

    root, output = report_project()
    lock = read_json_checked(root / "protocol.lock.json")
    result = read_json_checked(root / "confirmation.json")
    new_cell = deepcopy(lock["cells"][0]); new_cell.update(cell_id="third", model_id=2, baseline_id="third")
    lock["cells"].append(new_cell)
    new_row = deepcopy(result["summary"]["rows"][0]); new_row.update(new_cell)
    result["summary"]["rows"].append(new_row)
    for mid in range(3):
        cell = deepcopy(new_cell); cell.update(cell_id=f"ideal-{mid}", model_id=mid, model_kind="ideal_silence", detector_id="perfect", families=["ideal_silence/k1"])
        lock["cells"].append(cell)
        row = deepcopy(new_row); row.update(cell); row["intervals"]["R"] = [.01, .02]
        result["summary"]["rows"].append(row)
    lock["matrix_sha256"] = canonical_hash({"cells": lock["cells"]})
    lock["protocol_hash"] = canonical_hash({k: v for k, v in lock.items() if k != "protocol_hash"})
    result["protocol_hash"] = lock["protocol_hash"]
    for row in result["summary"]["rows"]:
        row["protocol_hash"] = lock["protocol_hash"]
    result["content_hash"] = canonical_hash({k: v for k, v in result.items() if k != "content_hash"})
    write_json_atomic(root / "protocol.lock.json", lock); write_json_atomic(root / "matrix.json", {"cells": lock["cells"]})
    write_json_atomic(root / "confirmation.json", result)
    write_json_atomic(root / "theorem/deterministic.json", {"status": "validated", "scope": "synthetic rendering fixture",
                      "ratios": [{"alpha": 1, "h": .01, "exact": .0000755, "leading": .000075, "ratio": 1.0066666667},
                                 {"alpha": 1, "h": .0001, "exact": .0000000075005, "leading": .0000000075, "ratio": 1.0000666667}]})
    def forbidden(*args, **kwargs):
        raise AssertionError("Plot regeneration cannot simulate")
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    manifest = render_report(root, output)
    assert all(value["status"] == "generated" for value in manifest["figures"].values())
    for figure in manifest["figures"].values():
        data = Path(figure["path"]).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", data[16:24])
        assert width >= 300 and height >= 300
