from dataclasses import replace
import hashlib
import io
import json
from urllib.error import HTTPError

import pytest


class ChunkedStream(io.BytesIO):
    def read(self, size=-1):
        assert 0 <= size <= 1024 * 1024, "unbounded input read"
        return super().read(min(size, 17))


CSV = b'NAME,SCAN,MJD,FREQ,NOTES\nTOI469.01,1,58961.1,1400000000,"line one\nline two"\nTOI469.01,1,58961.1,1400000001,x\nTOI469.01,2,58961.2,1400000002,x\n'


def test_stream_hashes_original_bytes_and_keeps_unique_scan_metadata():
    from seti_audit.data import stream_scan_metadata

    result = stream_scan_metadata(ChunkedStream(CSV), hashlib.sha256(CSV).hexdigest(),
                                  len(CSV), source_file="tiny.csv")
    assert result["actual_bytes"] == len(CSV)
    assert result["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert result["candidate_rows"] == 3
    assert len(result["scan_metadata"]) == 2
    assert result["scan_metadata"][1] == {
        "source_file": "tiny.csv", "NAME": "TOI469.01", "SCAN": "2", "MJD": "58961.2"
    }
    assert result["schedule_complete"] is False
    assert "line one\nline two" == result["sample_records"][0]["NOTES"]


def test_truncated_stream_cannot_become_valid_evidence():
    from seti_audit.data import stream_scan_metadata

    with pytest.raises(ValueError, match="size|hash"):
        stream_scan_metadata(ChunkedStream(CSV[:-1]), hashlib.sha256(CSV).hexdigest(), len(CSV))


def test_failed_stream_preserves_consumed_byte_accounting():
    from seti_audit.data import stream_scan_metadata

    consumed = []
    with pytest.raises(ValueError):
        stream_scan_metadata(ChunkedStream(CSV[:-1]), hashlib.sha256(CSV).hexdigest(), len(CSV),
                             on_bytes=consumed.append)
    assert sum(consumed) == len(CSV) - 1


def test_missing_time_column_cannot_create_schedule():
    from seti_audit.data import stream_scan_metadata

    raw = b"NAME,SCAN\nTOI469.01,1\n"
    with pytest.raises(ValueError, match="MJD"):
        stream_scan_metadata(io.BytesIO(raw), hashlib.sha256(raw).hexdigest(), len(raw))


def test_transient_http_failures_do_not_exhaust_an_attempt_quota():
    from seti_audit.acquisition import fetch_public

    failures = iter([429, 503, 503, 502, 429, None])

    def transport(request, **kwargs):
        status = next(failures)
        if status:
            raise HTTPError(request.full_url, status, "temporary", {}, None)
        return io.BytesIO(b"public data")

    with fetch_public("https://example.test/data", opener=transport, sleeper=lambda _: None) as stream:
        assert stream.read() == b"public data"


def test_authentication_failure_is_a_recordable_obstacle_not_credential_scraping():
    from seti_audit.acquisition import fetch_public

    def transport(request, **kwargs):
        raise HTTPError(request.full_url, 401, "authentication required", {}, None)

    with pytest.raises(HTTPError) as exc:
        fetch_public("https://example.test/data", opener=transport, sleeper=lambda _: None)
    assert exc.value.code == 401


def article_fixture(catalog):
    rows = []
    for row in catalog.source_rows:
        cells = [row["TOI"], "PC", "1", "1", "1", "1", row["distance_pc"],
                 row["RA_hms"], row["Dec_dms"]]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return "<html><table>" + "".join(rows) + "</table></html>"


def test_source_verification_checks_geometry_and_survives_offline_reload(repo_root, tmp_path):
    from seti_audit.data import load_catalog
    from seti_audit.acquisition import verify_catalog_source

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    article = tmp_path / "paper.html"
    article.write_text(article_fixture(catalog))
    checked = verify_catalog_source(catalog, article, tmp_path / "data")
    assert checked.provenance["source_status"] == "source_verified"
    assert load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data").provenance["source_status"] == "source_verified"
    article.write_text(article_fixture(catalog).replace("<td>68.19</td>", "<td>68.20</td>", 1))
    with pytest.raises(ValueError, match="469.01|geometry"):
        verify_catalog_source(catalog, article, tmp_path / "data")
    assert load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data").provenance["source_status"] == "blueprint_transcription"


def test_acquisition_preserves_real_access_reason_and_full_fallback(repo_root, tmp_path, monkeypatch):
    from seti_audit.contracts import load_protocol
    from seti_audit.data import acquire_sources, load_catalog
    from seti_audit.resources import ResourceLedger

    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    protocol = load_protocol(repo_root / "config/protocol.json")
    article = article_fixture(catalog).encode()
    files = {"_embedded": {"stash:files": [
        {"path": "tiny.csv", "size": len(CSV), "digest": hashlib.sha256(CSV).hexdigest(),
         "digestType": "sha-256", "_links": {"stash:download": {"href": "/api/v2/files/1/download"}}}
    ]}}

    def transport(request, **kwargs):
        url = request.full_url
        if "arxiv.org/html" in url:
            return io.BytesIO(article)
        if url.endswith("/versions/370211/files"):
            return io.BytesIO(json.dumps(files).encode())
        if url.endswith("/versions/370211"):
            return io.BytesIO(b'{"visibility":"public","_links":{}}')
        if "/download" in url:
            raise HTTPError(url, 401, "not authorized", {}, None)
        return io.BytesIO(b"<html>Public dataset description; no observing log.</html>")

    monkeypatch.chdir(tmp_path)
    result = acquire_sources(protocol, catalog, ResourceLedger(tmp_path / "results/usage.jsonl"),
                             opener=transport, sleeper=lambda _: None)
    assert result["schedule_grade"] == "coarsened_F1"
    assert result["detector_grade"] == "assumed_F2"
    assert any(item.get("http_status") == 401 for item in result["access_failures"])
    assert len(json.loads((tmp_path / "data/bounded_visits.json").read_text())["visits"]) == 62
