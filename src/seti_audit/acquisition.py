"""Ordinary public-source acquisition, transport integrity, and source checks."""

from dataclasses import replace
from datetime import datetime, timezone
from html.parser import HTMLParser
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .artifacts import read_json_checked, write_json_atomic
from .contracts import Catalog, Protocol
from .resources import ResourceLedger

ARTICLE_URL = "https://arxiv.org/html/2308.02712v4"
DRYAD = "https://datadryad.org"
VERSION_URL = DRYAD + "/api/v2/versions/370211"
LANDING_URL = DRYAD + "/dataset/doi:10.5061/dryad.wm37pvn0b"


def fetch_public(url: str, *, opener=None, sleeper=None):
    opener, sleeper = opener or urlopen, sleeper or time.sleep
    delay = 1.0
    while True:
        try:
            return opener(Request(url, headers={"User-Agent": "seti-silence-audit/0.1 scientific source audit"}))
        except HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
            print(f"Transient HTTP {exc.code}; retrying public source {url}", flush=True)
        except URLError as exc:
            wait = delay
            print(f"Connection unavailable for {url}: {exc.reason}; retrying", flush=True)
        sleeper(wait)
        delay = min(60.0, delay * 2)  # Connection backoff, never a project deadline.


class _HashingRaw(io.RawIOBase):
    def __init__(self, stream, on_bytes=None):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.count = 0
        self.on_bytes = on_bytes

    def readable(self):
        return True

    def readinto(self, buffer):
        chunk = self.stream.read(len(buffer))
        if not chunk:
            return 0
        self.digest.update(chunk)
        self.count += len(chunk)
        if self.on_bytes is not None:
            self.on_bytes(len(chunk))
        buffer[:len(chunk)] = chunk
        return len(chunk)


def stream_scan_metadata(stream, expected_sha256: str, expected_bytes: int,
                         *, source_file: str = "unknown", progress=None, on_bytes=None) -> dict:
    raw = _HashingRaw(stream, on_bytes=on_bytes)
    text = io.TextIOWrapper(io.BufferedReader(raw, buffer_size=1024 * 1024),
                            encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    if not {"NAME", "SCAN", "MJD"}.issubset(reader.fieldnames or ()):
        raise ValueError("Candidate CSV requires NAME, SCAN, and MJD")
    metadata, sample = {}, []
    rows = 0
    next_progress = 64 * 1024 * 1024
    for row in reader:
        name, scan, mjd = (row[key].strip() for key in ("NAME", "SCAN", "MJD"))
        if not math.isfinite(float(mjd)):
            raise ValueError("Nonfinite scan MJD")
        key = (name, scan, mjd)
        metadata.setdefault(key, {"source_file": source_file, "NAME": name, "SCAN": scan, "MJD": mjd})
        rows += 1
        if len(sample) < 8:
            sample.append(row)
        if progress is not None and raw.count >= next_progress:
            progress(raw.count, rows, len(metadata))
            next_progress += 64 * 1024 * 1024
    actual_digest = raw.digest.hexdigest()
    if raw.count != expected_bytes:
        raise ValueError(f"Candidate byte size mismatch: expected {expected_bytes}, received {raw.count}")
    if actual_digest != expected_sha256:
        raise ValueError(f"Candidate hash mismatch: expected {expected_sha256}, received {actual_digest}")
    return {"schema_version": 1, "source_file": source_file, "actual_bytes": raw.count,
            "sha256": actual_digest, "candidate_rows": rows, "scan_metadata": list(metadata.values()),
            "sample_records": sample, "schedule_complete": False,
            "completeness_note": "Candidate records alone do not establish absence of omitted zero-hit scans"}


class _SourceHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.links = [], []
        self.cell, self.row = None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append("".join(self.cell).strip().replace("−", "-"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def verify_catalog_source(catalog: Catalog, html_path: Path, output_dir: Path) -> Catalog:
    from .data import _sexagesimal

    content = Path(html_path).read_bytes()
    parser = _SourceHTML()
    parser.feed(content.decode("utf-8"))
    known = set(catalog.geometry.site_ids)
    rows = [r for r in parser.rows if len(r) == 9 and r[0] in known]
    if len(rows) != len(catalog.source_rows):
        raise ValueError(f"Published primary-target geometry count mismatch: found {len(rows)}")
    for source, planned in zip(rows, catalog.source_rows):
        if (source[0] != planned["TOI"] or float(source[6]) != float(planned["distance_pc"])
                or _sexagesimal(source[7], right_ascension=True) != _sexagesimal(planned["RA_hms"], right_ascension=True)
                or _sexagesimal(source[8], right_ascension=False) != _sexagesimal(planned["Dec_dms"], right_ascension=False)):
            raise ValueError(f"Published geometry mismatch for TOI {planned['TOI']}")
    provenance = catalog.provenance | {
        "source_status": "source_verified", "evidence_label": "Source observation",
        "source_verification": {"source_path": str(html_path), "sha256": hashlib.sha256(content).hexdigest(),
                                "url": ARTICLE_URL, "rows_checked": len(rows),
                                "fields_checked": ["TOI", "distance_pc", "RA_hms", "Dec_dms"]}}
    write_json_atomic(Path(output_dir) / "provenance.json", provenance)
    return replace(catalog, provenance=provenance)


def acquire_sources(protocol: Protocol, catalog: Catalog, ledger: ResourceLedger,
                    *, opener=None, sleeper=None) -> dict:
    from .data import load_schedule

    inputs, data = Path("inputs"), Path("data")
    inputs.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    manifest_path = inputs / "acquisition_manifest.json"
    previous = read_json_checked(manifest_path) if manifest_path.exists() else {}
    sources = previous.get("sources", [])
    failures = previous.get("access_failures", [])
    job = ledger.start("G0")
    started = time.perf_counter()
    downloaded = 0

    def record_bytes(count):
        nonlocal downloaded
        downloaded += count

    def record_failure(url, exc):
        item = {"url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "error": str(exc), "http_status": getattr(exc, "code", None)}
        failures.append(item)
        print(f"Source obstacle: {url}: {item['http_status']} {type(exc).__name__}", flush=True)

    def save_manifest(**extra):
        write_json_atomic(manifest_path, {"schema_version": 1, "sources": sources,
                          "access_failures": failures, "dataset_version": 370211, **extra})

    def small(url, filename):
        nonlocal downloaded
        path = inputs / filename
        cached = next((r for r in reversed(sources) if r.get("url") == url and r.get("path") == str(path)), None)
        if cached and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == cached.get("sha256"):
            return path.read_bytes()
        try:
            with fetch_public(url, opener=opener, sleeper=sleeper) as response:
                parts = []
                while chunk := response.read(65536):
                    downloaded += len(chunk)
                    parts.append(chunk)
            content = b"".join(parts)
            path.write_bytes(content)
            sources.append({"url": url, "path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
                            "bytes": len(content), "evidence_label": "Source observation",
                            "retrieved_utc": datetime.now(timezone.utc).isoformat(), "http_status": 200})
            save_manifest()
            return content
        except HTTPError as exc:
            record_failure(url, exc)
            save_manifest()
            return None

    try:
        article = small(ARTICLE_URL, "ucla_2308.02712v4.html")
        if article is not None:
            catalog = verify_catalog_source(catalog, inputs / "ucla_2308.02712v4.html", data)
        small(VERSION_URL, "dryad_version_370211.json")
        files_content = small(VERSION_URL + "/files", "dryad_files_370211.json")
        landing = small(LANDING_URL, "dryad_landing.html")
        page = _SourceHTML()
        if landing:
            page.feed(landing.decode("utf-8"))
        file_entries = json.loads(files_content).get("_embedded", {}).get("stash:files", []) if files_content else []
        extracted, file_status = [], []
        for entry in sorted(file_entries, key=lambda e: (e["path"] != "README.md", e["path"])):
            name = Path(entry["path"]).name
            href = entry.get("_links", {}).get("stash:download", {}).get("href")
            if not href:
                file_status.append({"path": name, "status": "missing_returned_download_link"})
                continue
            api_url = urljoin(DRYAD, href)
            file_id = re.search(r"/files/(\d+)/", api_url)
            routes = [api_url]
            if file_id:
                routes += [urljoin(DRYAD, link) for link in page.links
                           if re.search(r"/" + file_id.group(1) + r"(?:[/?#]|$)", link)]
            routes = list(dict.fromkeys(routes))
            if name == "README.md":
                for url in routes:
                    content = small(url, "dryad_README.md")
                    if content is not None:
                        if len(content) != entry["size"] or hashlib.sha256(content).hexdigest() != entry["digest"]:
                            raise ValueError("Archive README hash/size mismatch")
                        file_status.append({"path": name, "status": "verified", "sha256": entry["digest"]})
                        break
                else:
                    file_status.append({"path": name, "status": "access_obstacle", "routes": routes})
                continue
            if not name.endswith(".csv"):
                continue
            reduced_path = inputs / f"{name}.scan_metadata.json"
            if reduced_path.exists():
                cached = read_json_checked(reduced_path)
                if cached.get("sha256") == entry["digest"] and cached.get("actual_bytes") == entry["size"]:
                    extracted.extend(cached["scan_metadata"])
                    file_status.append({"path": name, "status": "verified_cached", "reduced_path": str(reduced_path)})
                    continue
            for url in routes:
                try:
                    print(f"Streaming {name} ({entry['size']} bytes) from returned public route", flush=True)
                    with fetch_public(url, opener=opener, sleeper=sleeper) as response:
                        result = stream_scan_metadata(response, entry["digest"], entry["size"], source_file=name,
                            on_bytes=record_bytes,
                            progress=lambda size, rows, scans: print(f"  {name}: {size} bytes, {rows} rows, {scans} scan keys", flush=True))
                    write_json_atomic(reduced_path, result)
                    extracted.extend(result["scan_metadata"])
                    sources.append({"url": url, "path": str(reduced_path), "original_sha256": result["sha256"],
                                    "bytes": result["actual_bytes"], "evidence_label": "Source observation",
                                    "retrieved_utc": datetime.now(timezone.utc).isoformat(), "http_status": 200})
                    file_status.append({"path": name, "status": "verified", "reduced_path": str(reduced_path)})
                    save_manifest(file_status=file_status)
                    break
                except HTTPError as exc:
                    record_failure(url, exc)
            else:
                file_status.append({"path": name, "status": "access_obstacle", "routes": routes})
        if extracted:
            write_json_atomic(inputs / "candidate_scan_metadata.json", {
                "schema_version": 1, "records": extracted, "schedule_complete": False,
                "reason": "Candidate detections require an independent selected-visit completeness check"})
        schedule = load_schedule(catalog, inputs, data)
        report = {"schema_version": 1, "sources": sources, "access_failures": failures,
                  "dataset_version": 370211, "file_status": file_status,
                  "catalog_status": catalog.provenance["source_status"],
                  "schedule_grade": schedule.schedule_grade, "detector_grade": schedule.detector_grade,
                  "selection_calibration": {"status": "assumed_F2", "reason":
                      "Published hit recovery and candidate records do not identify paired full-selection recovery"},
                  "downloaded_bytes_this_job": downloaded}
        write_json_atomic(manifest_path, report)
        ledger.finish(job, time.perf_counter() - started, 0, downloaded)
        return report
    except BaseException as exc:
        save_manifest(interrupted=True, exception=type(exc).__name__)
        ledger.finish(job, time.perf_counter() - started, 0, downloaded,
                      status="interrupted", details={"exception": type(exc).__name__})
        raise
