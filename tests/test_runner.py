from copy import deepcopy
from pathlib import Path

import pytest

from test_freeze import frozen_smoke, small_protocol


def test_complete_smoke_confirmation_and_repeat_resume_are_identical(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    ledger = ResourceLedger(root / "usage.jsonl")
    result = run_confirmation(frozen_smoke, False, ledger)
    assert result["status"] == "smoke_complete"
    assert result["protocol_hash"] == frozen_smoke["protocol_hash"]
    assert all(row["completion_status"] != "pending" for row in result["summary"]["rows"])
    usage = ledger.usage()
    repeated = run_confirmation(frozen_smoke, True, ledger)
    assert repeated == result
    assert ledger.usage() == usage


def test_interruption_mid_checkpoint_resumes_seed_and_counts(frozen_smoke, monkeypatch):
    import seti_audit.runner as runner
    from seti_audit.resources import ResourceLedger

    ledger = ResourceLedger(Path(frozen_smoke["_output_dir"]) / "usage.jsonl")
    original = runner.commit_batch
    published = []
    def interrupt_after_publication(*args, **kwargs):
        value = original(*args, **kwargs)
        published.append(value)
        if len(published) == 2:
            raise OSError("injected interruption after publication")
        return value
    monkeypatch.setattr(runner, "commit_batch", interrupt_after_publication)
    with pytest.raises(OSError):
        runner.run_confirmation(frozen_smoke, False, ledger)
    monkeypatch.setattr(runner, "commit_batch", original)
    result = runner.run_confirmation(frozen_smoke, True, ledger)
    assert result["status"] == "smoke_complete"
    assert all(batch["protocol_hash"] == frozen_smoke["protocol_hash"] for batch in result["batches"])
    assert len({b["batch_id"] for b in result["batches"]}) == len(result["batches"])
    assert ledger.pending_jobs() == []


def test_resume_leaves_unrelated_live_accounting_job_alone(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger

    ledger = ResourceLedger(Path(frozen_smoke["_output_dir"]) / "usage.jsonl")
    parent = ledger.start("G4")
    run_confirmation(frozen_smoke, False, ledger)
    assert [job["job_id"] for job in ledger.pending_jobs()] == [parent]


def test_large_previous_usage_never_prevents_confirmation(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger

    ledger = ResourceLedger(Path(frozen_smoke["_output_dir"]) / "usage.jsonl")
    job = ledger.start("G4")
    ledger.finish(job, 1e12, 10**12, download_bytes=10**12)
    result = run_confirmation(frozen_smoke, False, ledger)
    assert result["status"] == "smoke_complete"
    assert ledger.usage()["history_evaluations"] > 10**12


def test_resume_rejects_changed_derived_results(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.artifacts import read_json_checked, write_json_atomic
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    ledger = ResourceLedger(root / "usage.jsonl")
    run_confirmation(frozen_smoke, False, ledger)
    result = read_json_checked(root / "confirmation.json")
    result["summary"]["rows"][0]["intervals"]["R0"] = [.9, .99]
    write_json_atomic(root / "confirmation.json", result)
    with pytest.raises(ValueError, match="hash"):
        run_confirmation(frozen_smoke, True, ledger)
