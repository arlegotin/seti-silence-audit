"""Physical catalog reconciliation and evidence-graded observing schedules."""

from collections import defaultdict
from dataclasses import asdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import math
from pathlib import Path
import re

import numpy as np

from .artifacts import read_json_checked, write_json_atomic
from .contracts import BoundedVisit, Catalog, Geometry, Scan, Schedule

SECONDS_PER_YEAR = 365.25 * 86400
ON_DURATION_YEARS = 150 / SECONDS_PER_YEAR
PC_TO_LY = (648000 / math.pi) * 149597870700 / (299792458 * SECONDS_PER_YEAR)
SESSION_GROUPS = {"2020-2021": ("2020-04-22", "2021-04-28"),
                  "2022-2023": ("2022-05-22", "2023-05-13")}
MJD_EPOCH = datetime(1858, 11, 17, tzinfo=timezone.utc)


def _sexagesimal(value: str, *, right_ascension: bool) -> float:
    fields = value.lstrip("+-").split(":")
    if len(fields) != 3:
        raise ValueError(f"Invalid sexagesimal coordinate: {value}")
    degree, minute, second = map(float, fields)
    limit = 24 if right_ascension else 90
    if (not all(math.isfinite(x) for x in (degree, minute, second))
            or not 0 <= minute < 60 or not 0 <= second < 60
            or not 0 <= degree <= limit or (degree == limit and (right_ascension or minute or second))):
        raise ValueError(f"Invalid sexagesimal coordinate: {value}")
    sign = -1 if value.startswith("-") else 1
    if right_ascension and sign < 0:
        raise ValueError("Negative right ascension")
    return math.radians(sign * (degree + minute / 60 + second / 3600)
                        * (15 if right_ascension else 1))


def _write_csv(path: Path, fields: list[str], rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_catalog(blueprint_path: Path, output_dir: Path) -> Catalog:
    old_path = Path(output_dir) / "provenance.json"
    old_provenance = read_json_checked(old_path) if old_path.exists() else {}
    content = Path(blueprint_path).read_bytes()
    block = re.search(r"```csv\n(source_row,year_group,TOI,distance_pc,RA_hms,Dec_dms\n.*?)\n```",
                      content.decode("utf-8"), re.S)
    if block is None:
        raise ValueError("Missing published primary-target transcription")
    rows = tuple(dict(row) for row in csv.DictReader(io.StringIO(block.group(1))))
    if len(rows) != 62 or len({r["source_row"] for r in rows}) != len(rows):
        raise ValueError("Expected 62 distinct published source rows")
    unique = {}
    linked_rows = defaultdict(list)
    for row in rows:
        distance = float(row["distance_pc"])
        if not math.isfinite(distance) or distance <= 0 or row["year_group"] not in SESSION_GROUPS:
            raise ValueError("Invalid target distance or year group")
        ra = _sexagesimal(row["RA_hms"], right_ascension=True)
        dec = _sexagesimal(row["Dec_dms"], right_ascension=False)
        site_id = row["TOI"]
        signature = (distance, ra, dec)
        if site_id in unique and unique[site_id][0] != signature:
            raise ValueError(f"Conflicting physical-site rows: TOI {site_id}")
        unique.setdefault(site_id, (signature, row))
        linked_rows[site_id].append(row["source_row"])
    radii = np.array([value[0][0] * PC_TO_LY for value in unique.values()])
    xyz = np.array([r * np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra),
                                 math.sin(dec)])
                    for r, ((_, ra, dec), _) in zip(radii, unique.values())])
    geometry = Geometry(tuple(unique), xyz, radii, np.linalg.norm(xyz[:, None] - xyz[None, :], axis=2))
    provenance = {"schema_version": 1, "evidence_label": "Planning transcription",
                  "source_status": "blueprint_transcription", "source_rows": len(rows),
                  "physical_sites": len(unique), "blueprint_sha256": hashlib.sha256(content).hexdigest(),
                  "duplicate_sites": {key: value for key, value in linked_rows.items() if len(value) > 1},
                  "pc_to_ly": PC_TO_LY, "coordinates": "fixed nominal heliocentric Cartesian"}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "source_rows.csv", list(rows[0]), rows)
    targets = [dict(site_id=site, distance_pc=unique[site][1]["distance_pc"],
                    distance_ly=float(radii[i]), RA_hms=unique[site][1]["RA_hms"],
                    Dec_dms=unique[site][1]["Dec_dms"], x_ly=float(xyz[i, 0]),
                    y_ly=float(xyz[i, 1]), z_ly=float(xyz[i, 2]), source_rows=";".join(linked_rows[site]))
               for i, site in enumerate(unique)]
    _write_csv(output_dir / "targets.csv", list(targets[0]), targets)
    np.savez_compressed(output_dir / "geometry.npz", xyz_ly=xyz, radii_ly=radii,
                        distances_ly=geometry.distances_ly)
    provenance["artifact_hashes"] = {name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
                                      for name in ("source_rows.csv", "targets.csv", "geometry.npz")}
    write_json_atomic(output_dir / "provenance.json", provenance)
    catalog = Catalog(rows, geometry, provenance)
    verification = old_provenance.get("source_verification", {})
    verified_path = Path(verification.get("source_path", ""))
    if (old_provenance.get("blueprint_sha256") == provenance["blueprint_sha256"]
            and verified_path.is_file()
            and hashlib.sha256(verified_path.read_bytes()).hexdigest() == verification.get("sha256")):
        from .acquisition import verify_catalog_source
        catalog = verify_catalog_source(catalog, verified_path, output_dir)
    return catalog


def _utc(date: str) -> datetime:
    return datetime.fromisoformat(date).replace(tzinfo=timezone.utc)


def load_schedule(catalog: Catalog, input_dir: Path, output_dir: Path) -> Schedule:
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = input_dir / "observing_log.json"
    if log_path.exists():
        raw = read_json_checked(log_path)
        if raw.get("kind") != "observing_log" or not raw.get("scans"):
            raise ValueError("Exact schedule requires observing-log evidence")
        records = raw["scans"]
        endpoint_mjd = max(float(row["start_mjd"]) + float(row["duration_s"]) / 86400 for row in records)
        scans = tuple(Scan(str(row["visit_id"]), str(row["site_id"]), int(row["scan_index"]),
                           (float(row["start_mjd"]) - endpoint_mjd) / 365.25,
                           float(row["duration_s"]) / SECONDS_PER_YEAR, str(row["paired_visit_id"]),
                           str(row["source_row"]), row["session_date"], float(row["start_mjd"]),
                           row["source_file"]) for row in records)
        provenance = {"source_status": raw.get("provenance_status", "source_observing_log"),
                      "source_path": str(log_path.resolve()),
                      "source_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
                      "time_scale": raw.get("time_scale", "UTC assumed; archive scale not independently established")}
        schedule = Schedule(scans, (), "exact", "assumed_F2", {"t0_mjd": endpoint_mjd}, provenance)
        completeness = provenance | {"kind": "observing_log"}
        validation = validate_schedule(schedule, catalog, completeness)
        write_json_atomic(output_dir / "schedule_validation.json", validation)
        fields = ["visit_id", "site_id", "session_date", "scan_index", "start_mjd", "duration_s",
                  "end_mjd", "paired_visit_id", "source_file", "provenance_status"]
        _write_csv(output_dir / "visits.csv", fields,
                   [dict(visit_id=s.visit_id, site_id=s.site_id, session_date=s.session_date,
                         scan_index=s.scan_index, start_mjd=s.start_mjd, duration_s=150,
                         end_mjd=s.start_mjd + 150 / 86400, paired_visit_id=s.paired_visit_id,
                         source_file=s.source_file, provenance_status=provenance["source_status"])
                    for s in scans])
        return schedule
    endpoint_lo, endpoint_hi = _utc("2023-05-13"), _utc("2023-05-15")
    visits = []
    for row in catalog.source_rows:
        intervals = tuple(((start - endpoint_hi).total_seconds() / SECONDS_PER_YEAR,
                           min(0.0, (start + timedelta(days=2) - endpoint_lo).total_seconds() / SECONDS_PER_YEAR))
                          for start in map(_utc, SESSION_GROUPS[row["year_group"]]))
        visits.append(BoundedVisit(f"row-{row['source_row']}", row["TOI"], intervals,
                                   ON_DURATION_YEARS, row["source_row"], row["year_group"]))
    schedule = Schedule((), tuple(visits), "coarsened_F1", "assumed_F2",
                        {"lower_utc": "2023-05-13T00:00:00Z", "upper_utc": "2023-05-15T00:00:00Z"},
                        {"source_status": "blueprint_transcription", "exact_log_available": False,
                         "assumptions": ["UTC session-date interpretation", "48-hour session windows",
                                         "unknown session alternative and ON gap; two nonoverlapping 150s scans"]})
    write_json_atomic(output_dir / "bounded_visits.json", {
        "schema_version": 1, "schedule_grade": schedule.schedule_grade,
        "detector_grade": schedule.detector_grade, "endpoint": schedule.endpoint,
        "provenance": schedule.provenance, "visits": [asdict(v) for v in visits]})
    return schedule


def validate_schedule(schedule: Schedule, catalog: Catalog, completeness: dict) -> dict:
    if schedule.schedule_grade != "exact":
        return {"schema_version": 1, "schedule_grade": schedule.schedule_grade,
                "exact_complete": False, "reason": "Interval-valued observation, no exact scan imputation"}
    source_path = Path(completeness.get("source_path", ""))
    if (completeness.get("kind") != "observing_log" or not source_path.is_file()
            or hashlib.sha256(source_path.read_bytes()).hexdigest() != completeness.get("source_sha256")):
        raise ValueError("Missing source-backed observing-log completeness evidence")
    source = read_json_checked(source_path)
    if source.get("kind") != "observing_log" or len(source.get("scans", ())) != len(schedule.exact_scans):
        raise ValueError("Observing-log evidence does not match selected scans")
    source_rows = source["scans"]
    endpoint_mjd = max(float(row["start_mjd"]) + float(row["duration_s"]) / 86400
                       for row in source_rows)
    if schedule.endpoint.get("t0_mjd") != endpoint_mjd:
        raise ValueError("Endpoint disagrees with observing-log evidence")
    original = sorted((str(r["visit_id"]), str(r["site_id"]), int(r["scan_index"]),
                       float(r["start_mjd"]), float(r["duration_s"]) / SECONDS_PER_YEAR,
                       str(r["source_row"]), r["session_date"], str(r["paired_visit_id"]))
                      for r in source_rows)
    normalized = sorted((s.visit_id, s.site_id, s.scan_index, s.start_mjd, s.duration_year,
                         s.source_row, s.session_date, s.paired_visit_id) for s in schedule.exact_scans)
    if original != normalized:
        raise ValueError("Selected scans disagree with observing-log evidence")
    if any(s.start_year != (s.start_mjd - endpoint_mjd) / 365.25 for s in schedule.exact_scans):
        raise ValueError("Relative scan times disagree with endpoint evidence")
    expected = {r["source_row"]: r for r in catalog.source_rows}
    groups = defaultdict(list)
    for scan in schedule.exact_scans:
        if scan.site_id not in catalog.geometry.site_ids or scan.source_row not in expected:
            raise ValueError("Unknown observing target/source row")
        row = expected[scan.source_row]
        if row["TOI"] != scan.site_id or scan.session_date not in SESSION_GROUPS[row["year_group"]]:
            raise ValueError("Observing source identity/session mismatch")
        if (scan.start_mjd is None or not math.isfinite(scan.start_mjd)
                or not math.isfinite(scan.start_year) or not math.isfinite(scan.duration_year)
                or not math.isclose(scan.duration_year, ON_DURATION_YEARS, rel_tol=1e-12)):
            raise ValueError("Invalid scan timing/duration")
        day = (_utc(scan.session_date) - MJD_EPOCH).days
        if not day <= scan.start_mjd < day + 2:
            raise ValueError("Timestamp outside its session dates")
        groups[scan.visit_id].append(scan)
    covered_rows = []
    for visit_id, scans in groups.items():
        if len(scans) != 2 or {s.scan_index for s in scans} != {1, 2}:
            raise ValueError("Every visit requires both ON scans, including zero-hit scans")
        if len({(s.site_id, s.source_row, s.session_date, s.paired_visit_id) for s in scans}) != 1:
            raise ValueError("Inconsistent linked-visit identity")
        first, second = sorted(scans, key=lambda s: s.scan_index)
        if first.start_year + first.duration_year > second.start_year + 2e-11 / 365.25:
            raise ValueError("Overlapping or reordered ON scans")
        partner = groups.get(first.paired_visit_id, [])
        if len(partner) != 2 or any(p.paired_visit_id != visit_id for p in partner):
            raise ValueError("Missing reciprocal ABAB partner")
        sequence = sorted(scans + partner, key=lambda s: s.start_year)
        if ([s.visit_id for s in sequence] not in
                ([visit_id, first.paired_visit_id] * 2, [first.paired_visit_id, visit_id] * 2)):
            raise ValueError("Invalid ABAB chronology")
        if any(a.start_year + a.duration_year > b.start_year + 2e-11 / 365.25
               for a, b in zip(sequence, sequence[1:])):
            raise ValueError("Overlapping ABAB scans")
        covered_rows.append(first.source_row)
    if len(covered_rows) != len(expected) or set(covered_rows) != set(expected):
        raise ValueError("Observing log does not cover every published visit, including zero-hit targets")
    sessions = {s.session_date for s in schedule.exact_scans}
    if sessions != {date for group in SESSION_GROUPS.values() for date in group}:
        raise ValueError("Incomplete survey session coverage")
    return {"schema_version": 1, "schedule_grade": "exact", "exact_complete": True,
            "visits": len(groups), "scans": len(schedule.exact_scans), "sessions": sorted(sessions),
            "source_evidence": completeness, "timestamp_roundoff_tolerance_days": 2e-11}


from .acquisition import acquire_sources, stream_scan_metadata  # Public input boundary.
