import fcntl
import json
from pathlib import Path
import subprocess
import sys

import pytest


def test_usage_does_not_terminate_work(tmp_path):
    from seti_audit.resources import ResourceLedger

    path = tmp_path / "resources.jsonl"
    ledger = ResourceLedger(path)
    first = ledger.start("G1", ensemble_id=7)
    ledger.finish(first, elapsed_seconds=1e12, history_evaluations=10**12, download_bytes=10**12)
    second = ledger.start("G4", ensemble_id=7)
    ledger.finish(second, elapsed_seconds=2, history_evaluations=3)
    assert ResourceLedger(path).usage()["history_evaluations"] == 10**12 + 3
    assert ResourceLedger(path).usage()["elapsed_seconds"] == 1e12 + 2


def test_job_record_survives_crash_and_cannot_finish_twice(tmp_path):
    from seti_audit.resources import ResourceLedger

    path = tmp_path / "resources.jsonl"
    job = ResourceLedger(path).start("G4", ensemble_id=2)
    restarted = ResourceLedger(path)
    assert restarted.pending_jobs()[0]["job_id"] == job
    restarted.finish(job, elapsed_seconds=3, history_evaluations=100)
    assert ResourceLedger(path).pending_jobs() == []
    with pytest.raises(ValueError, match="finished"):
        ResourceLedger(path).finish(job, elapsed_seconds=3, history_evaluations=100)
    assert ResourceLedger(path).usage()["history_evaluations"] == 100


def test_bootstrap_import_is_exactly_once(tmp_path):
    from seti_audit.resources import ResourceLedger

    source = tmp_path / "bootstrap.jsonl"
    source.write_text(json.dumps({"job_id": "bootstrap-1", "elapsed_seconds": 4.0}) + "\n")
    ledger = ResourceLedger(tmp_path / "resources.jsonl")
    ledger.import_bootstrap(source)
    ledger.import_bootstrap(source)
    assert ledger.usage()["elapsed_seconds"] == 4.0


def test_concurrent_writer_is_rejected_without_partial_record(tmp_path):
    from seti_audit.resources import ResourceLedger

    path = tmp_path / "resources.jsonl"
    with (tmp_path / "resources.jsonl.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            ResourceLedger(path).start("G1")
    assert not path.exists()


def test_logged_command_keeps_actual_exit_status(tmp_path):
    ledger = tmp_path / "resources.jsonl"
    result = subprocess.run(
        [sys.executable, "-m", "seti_audit", "run-logged", "--stage", "G1",
         "--ledger", str(ledger), "--", sys.executable, "-c", "raise SystemExit(7)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 7, result.stderr
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert records[-1]["status"] == "failed"
    assert records[-1]["details"]["returncode"] == 7
    assert records[-1]["details"]["max_rss_bytes"] > 0
    assert records[-1]["details"]["free_disk_bytes"] >= 0


def test_preflight_measures_capacity_and_rejects_actual_disk_shortage(tmp_path, monkeypatch):
    from collections import namedtuple
    import errno
    import seti_audit.resources as resources

    measured = resources.resource_preflight(tmp_path, bytes_required=1)
    assert measured["disk_free_bytes"] > 0
    assert measured["available_memory_bytes"] is None or measured["available_memory_bytes"] > 0
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(resources.shutil, "disk_usage", lambda path: usage(100, 100, 0))
    with pytest.raises(OSError) as failure:
        resources.resource_preflight(tmp_path, bytes_required=1024)
    assert failure.value.errno == errno.ENOSPC
