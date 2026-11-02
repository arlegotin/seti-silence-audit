from datetime import datetime, timezone
from dataclasses import replace
import json

import numpy as np
import pytest


def test_catalog_has_physical_sites_and_all_original_rows(repo_root, tmp_path):
    from seti_audit.data import load_catalog

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path)
    geometry = catalog.geometry
    assert len(catalog.source_rows) == 62
    assert len(geometry.site_ids) == 61
    assert [r["source_row"] for r in catalog.source_rows if r["TOI"] == "1730.01"] == ["15", "38"]
    assert geometry.xyz_ly[geometry.site_ids.index("546.01"), 2] < 0
    assert geometry.radii_ly.min() == pytest.approx(30.7891621, abs=1e-7)
    assert {s for s, r in zip(geometry.site_ids, geometry.radii_ly) if r < 100} == {
        "488.01", "562.01", "1726.01", "1821.01", "1468.01", "5084.01"
    }
    np.testing.assert_array_equal(np.diag(geometry.distances_ly), 0)
    np.testing.assert_array_equal(geometry.distances_ly, geometry.distances_ly.T)
    assert catalog.provenance["source_status"] == "blueprint_transcription"
    assert (tmp_path / "source_rows.csv").exists()
    assert (tmp_path / "targets.csv").exists()
    with np.load(tmp_path / "geometry.npz") as saved:
        np.testing.assert_array_equal(saved["distances_ly"], geometry.distances_ly)


def test_conflicting_duplicate_is_rejected_before_output(repo_root, tmp_path):
    from seti_audit.data import load_catalog

    bad = tmp_path / "bad.md"
    bad.write_text((repo_root / "docs/blueprint.md").read_text().replace(
        "38,2022-2023,1730.01,35.69", "38,2022-2023,1730.01,35.70"))
    with pytest.raises(ValueError, match="Conflicting"):
        load_catalog(bad, tmp_path / "output")
    assert not (tmp_path / "output/targets.csv").exists()


@pytest.mark.parametrize("value", ["-1", "nan", "inf", "0"])
def test_invalid_catalog_distance_is_rejected(repo_root, tmp_path, value):
    from seti_audit.data import load_catalog

    bad = tmp_path / "bad.md"
    bad.write_text((repo_root / "docs/blueprint.md").read_text().replace(
        "1,2020-2021,469.01,68.19", f"1,2020-2021,469.01,{value}"))
    with pytest.raises(ValueError):
        load_catalog(bad, tmp_path / "output")


def test_coarsened_schedule_retains_date_unions_without_scan_imputation(repo_root, tmp_path):
    from seti_audit.data import load_catalog, load_schedule

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    assert schedule.schedule_grade == "coarsened_F1"
    assert schedule.detector_grade == "assumed_F2"
    assert not schedule.exact_scans
    assert len(schedule.bounded_visits) == 62
    assert all(len(v.allowed_intervals) == 2 for v in schedule.bounded_visits)
    assert all(v.duration_year == 150 / (365.25 * 86400) for v in schedule.bounded_visits)
    assert schedule.endpoint["lower_utc"] == "2023-05-13T00:00:00Z"
    assert schedule.endpoint["upper_utc"] == "2023-05-15T00:00:00Z"
    final_component = schedule.bounded_visits[-1].allowed_intervals[-1]
    assert final_component == (-2 / 365.25, 0.0)
    assert not (tmp_path / "data/visits.csv").exists()
    saved = json.loads((tmp_path / "data/bounded_visits.json").read_text())
    assert saved["schedule_grade"] == "coarsened_F1"
    assert "start_mjd" not in saved["visits"][0]


def test_boolean_completeness_claim_cannot_certify_exact_schedule(repo_root, tmp_path):
    from seti_audit.contracts import Scan, Schedule
    from seti_audit.data import load_catalog, validate_schedule

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    scans = tuple(Scan("v1", "469.01", j, -j / 365.25, 150 / (365.25 * 86400), "v2")
                  for j in (1, 2))
    schedule = Schedule(scans, (), "exact", "assumed_F2", {}, {})
    with pytest.raises(ValueError, match="evidence"):
        validate_schedule(schedule, catalog, {"complete": True})


def test_exact_log_requires_all_visits_and_valid_abab_pairing(repo_root, tmp_path):
    from seti_audit.data import load_catalog, load_schedule

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    records = []
    mjd_epoch = datetime(1858, 11, 17, tzinfo=timezone.utc)
    rows = catalog.source_rows
    for pair in range(31):
        a, b = rows[2 * pair:2 * pair + 2]
        date = ("2020-04-22" if pair < 8 else "2021-04-28" if pair < 16
                else "2022-05-22" if pair < 24 else "2023-05-13")
        base = (datetime.fromisoformat(date).replace(tzinfo=timezone.utc) - mjd_epoch).days
        for member, row in enumerate((a, b)):
            for scan in (1, 2):
                records.append(dict(
                    visit_id=f"row-{row['source_row']}", site_id=row["TOI"],
                    source_row=row["source_row"], session_date=date, scan_index=scan,
                    start_mjd=base + (pair * 700 + (scan - 1) * 300 + member * 150) / 86400,
                    duration_s=150, paired_visit_id=f"row-{(b, a)[member]['source_row']}",
                    source_file="synthetic_control",
                ))
    directory = tmp_path / "inputs"
    directory.mkdir()
    log = directory / "observing_log.json"
    log.write_text(json.dumps({"schema_version": 1, "kind": "observing_log",
                               "provenance_status": "synthetic_control", "scans": records}))
    exact = load_schedule(catalog, directory, tmp_path / "data")
    assert exact.schedule_grade == "exact"
    assert len(exact.exact_scans) == 124
    assert exact.provenance["source_status"] == "synthetic_control"
    assert max(s.start_year + s.duration_year for s in exact.exact_scans) == pytest.approx(0, abs=1e-13)
    from seti_audit.data import validate_schedule
    shifted = replace(exact, exact_scans=tuple(replace(s, start_year=s.start_year - 1)
                                              for s in exact.exact_scans))
    with pytest.raises(ValueError, match="endpoint|relative|evidence"):
        validate_schedule(shifted, catalog, exact.provenance | {"kind": "observing_log"})
    records[-1]["start_mjd"] = records[-2]["start_mjd"]
    log.write_text(json.dumps({"schema_version": 1, "kind": "observing_log",
                               "provenance_status": "synthetic_control", "scans": records}))
    with pytest.raises(ValueError):
        load_schedule(catalog, directory, tmp_path / "bad-output")
