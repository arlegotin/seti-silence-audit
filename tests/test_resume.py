from pathlib import Path

import numpy as np
import pytest

from test_freeze import frozen_smoke, small_protocol


def test_batch_publication_is_idempotent_and_detects_conflicts(tmp_path):
    from seti_audit.artifacts import commit_batch, load_committed_batches

    payload = {"protocol_hash": "p", "counts": {"n": 7}}
    first = commit_batch(tmp_path, "batch-0", payload, {"x": np.arange(7)})
    assert commit_batch(tmp_path, "batch-0", payload, {"x": np.arange(7)}) == first
    rows = load_committed_batches(tmp_path, "p")
    assert len(rows) == 1
    np.testing.assert_array_equal(rows[0]["_arrays"]["x"], np.arange(7))
    with pytest.raises(ValueError, match="(?i)conflict"):
        commit_batch(tmp_path, "batch-0", dict(payload, counts={"n": 8}), {"x": np.arange(8)})


def test_finish_cannot_erase_already_recorded_work(tmp_path):
    from seti_audit.resources import ResourceLedger

    ledger = ResourceLedger(tmp_path / "usage.jsonl")
    job = ledger.start("G4")
    ledger.progress(job, 3., 12)
    with pytest.raises(ValueError, match="decrease"):
        ledger.finish(job, 2., 10)
    assert ledger.usage()["history_evaluations"] == 12


def test_published_orphan_recovers_after_manifest_write_failure(tmp_path, monkeypatch):
    import seti_audit.storage as storage

    original = storage._append_commit
    def fail(*args, **kwargs):
        raise OSError("injected manifest interruption")
    monkeypatch.setattr(storage, "_append_commit", fail)
    with pytest.raises(OSError):
        storage.commit_batch(tmp_path, "batch-0", {"protocol_hash": "p", "n": 4}, {})
    monkeypatch.setattr(storage, "_append_commit", original)
    assert len(storage.load_committed_batches(tmp_path, "p")) == 1
    assert len(storage.load_committed_batches(tmp_path, "p")) == 1
    assert len((tmp_path / "checkpoints/commits.jsonl").read_text().splitlines()) == 1


def test_corrupted_or_wrong_protocol_batches_cannot_be_imported(tmp_path):
    from seti_audit.artifacts import commit_batch, load_committed_batches

    commit_batch(tmp_path, "batch-0", {"protocol_hash": "p"}, {"x": np.arange(7)})
    with pytest.raises(ValueError, match="protocol"):
        load_committed_batches(tmp_path, "different")
    (tmp_path / "checkpoints/batch-0/arrays.npz").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        load_committed_batches(tmp_path, "p")


def test_interrupted_progress_counts_usage_once(tmp_path):
    from seti_audit.resources import ResourceLedger

    ledger = ResourceLedger(tmp_path / "usage.jsonl")
    job = ledger.start("G4")
    ledger.progress(job, 2., 10)
    ledger.progress(job, 3., 12)
    assert ledger.usage()["history_evaluations"] == 12
    ledger.finish(job, 4., 15)
    assert ledger.usage()["history_evaluations"] == 15
    assert ledger.usage()["elapsed_seconds"] == 4.
