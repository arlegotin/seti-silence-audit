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
    assert len(result["reference_checks"]) == 2
    assert all(row["trials"] == 8 for row in result["reference_checks"])
    assert all(seed[1] == 0 for batch in result["batches"] for seed in batch["seed_roots"].values())
    total = result["execution_totals"]["groups"]["interacting:0"]
    assert total["sampled_histories"] == total["attempted_proposals"] == 8
    assert total["history_evaluations"] >= 32
    replay = next(b for b in result["replay_samples"] if b["group_id"] == "interacting:0")
    from seti_audit.contracts import FirstClocks, Geometry
    from seti_audit.model import simulate_history
    import numpy as np
    history = simulate_history(FirstClocks(np.array([np.inf if x is None else x for x in replay["birth_years"]]),
                                           np.array(replay["speeds"]), np.array(replay["speed_gaps"])),
                               Geometry(**frozen_smoke["geometry"]))
    assert history.accepted_indices.tolist() == replay["accepted_indices"]
    assert history.arrives_within_horizon == replay["arrives_within_horizon"]
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


def test_explicit_extension_keeps_old_counts_seeds_lock_and_checkpoint_evidence(frozen_smoke):
    from seti_audit.experiments import run_confirmation, request_precision_extension
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    ledger = ResourceLedger(root / "usage.jsonl")
    first = run_confirmation(frozen_smoke, False, ledger)
    request_precision_extension(frozen_smoke, ["interacting:0"])
    extended = run_confirmation(frozen_smoke, True, ledger)
    assert extended["protocol_hash"] == first["protocol_hash"]
    assert extended["looks"]["interacting:0"] == 2
    assert extended["looks"]["ideal:0"] == 1
    assert {b["batch_id"]: b["seed_roots"] for b in first["batches"]}.items() <= {b["batch_id"]: b["seed_roots"] for b in extended["batches"]}.items()
    assert set(first["checkpoint_history"]) < set(extended["checkpoint_history"])
    row = next(r for r in extended["summary"]["rows"] if r["cell_id"] == "interacting:m0:k1:E0:Dnone")
    assert row["counts"]["histories"] == 16
    old_interval = first["summary"]["interval_evidence"]["interacting:m0:k1:R0"]
    new_interval = extended["summary"]["interval_evidence"]["interacting:m0:k1:R0"]
    assert new_interval["alpha"] == old_interval["alpha"] / 3
    assert new_interval["interval"][1] < old_interval["interval"][1]


def test_corrupt_checkpoint_state_cannot_choose_a_new_statistical_look(frozen_smoke, monkeypatch):
    import seti_audit.runner as runner
    from seti_audit.artifacts import read_json_checked, write_json_atomic
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    ledger = ResourceLedger(root / "usage.jsonl")
    original = runner.commit_batch
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("injected interruption")
    monkeypatch.setattr(runner, "commit_batch", fail)
    with pytest.raises(OSError):
        runner.run_confirmation(frozen_smoke, False, ledger)
    monkeypatch.setattr(runner, "commit_batch", original)
    state = read_json_checked(root / "run_state.json")
    state["looks"]["interacting:0"] = 2
    write_json_atomic(root / "run_state.json", state)
    with pytest.raises(ValueError, match="state.*hash"):
        runner.run_confirmation(frozen_smoke, True, ledger)


@pytest.mark.parametrize("small_protocol", [15], indirect=True)
def test_diagnostic_interruption_matches_uninterrupted_counts_and_seed_streams(frozen_smoke, monkeypatch, tmp_path):
    import shutil
    import seti_audit.runner as runner
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    clean_root = tmp_path / "clean"
    shutil.copytree(root, clean_root)
    clean = dict(frozen_smoke, _output_dir=str(clean_root))
    expected = runner.run_confirmation(clean, False, ResourceLedger(clean_root / "usage.jsonl"))
    ledger = ResourceLedger(root / "usage.jsonl")
    original = runner.commit_batch
    def fail(*args, **kwargs):
        value = original(*args, **kwargs)
        if args[2]["kind"] == "diagnostic":
            raise OSError("injected diagnostic interruption")
        return value
    monkeypatch.setattr(runner, "commit_batch", fail)
    with pytest.raises(OSError):
        runner.run_confirmation(frozen_smoke, False, ledger)
    monkeypatch.setattr(runner, "commit_batch", original)
    actual = runner.run_confirmation(frozen_smoke, True, ledger)
    assert actual["summary"] == expected["summary"]
    assert actual["batches"] == expected["batches"]
    assert ledger.pending_jobs() == []


def test_concurrent_confirmation_writer_is_rejected(frozen_smoke):
    import fcntl
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    ledger = ResourceLedger(root / "usage.jsonl")
    with (root / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            run_confirmation(frozen_smoke, False, ledger)
    assert ledger.usage()["history_evaluations"] == 0


def test_run_cli_uses_frozen_root_and_preserves_resume(frozen_smoke):
    from seti_audit.cli import main

    path = str(Path(frozen_smoke["_output_dir"]) / "protocol.lock.json")
    assert main(["run", "--protocol", path]) == 0
    assert main(["run", "--protocol", path, "--resume"]) == 0


def test_published_history_batches_retain_numerical_audit_metadata(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.artifacts import load_committed_batches
    from seti_audit.resources import ResourceLedger

    root = Path(frozen_smoke["_output_dir"])
    run_confirmation(frozen_smoke, False, ResourceLedger(root / "usage.jsonl"))
    for batch in load_committed_batches(root, frozen_smoke["protocol_hash"]):
        if batch["kind"] != "shell":
            audit = batch["numerical_diagnostics"]
            assert audit["speed_rounding_count"] >= 0
            assert audit["speed_rounding_mass_bound"] >= 0
            assert audit["history_scalar_rechecks"] >= 0


def test_freeze_cli_accepts_slow_projection_without_changing_smoke_scope(frozen_smoke, tmp_path):
    from seti_audit.artifacts import write_json_atomic, read_json_checked
    from seti_audit.cli import main

    config = tmp_path / "smoke.json"
    write_json_atomic(config, frozen_smoke["config"])
    calibration = {"initial_survivors": {"0": 8}, "initial_diagnostic_proposals": {}, "logical_batch_size": 4,
                   "projected_seconds": 1e12, "proposal_costs": {"0": 1e6}, "acceptance_bounds": {"0": {"low": .1, "high": 1.}},
                   "timings": {}, "rss_bytes": 1000, "execution_recommendations": ["schedule all work"], "evidence_ids": ["smoke-only"]}
    pilot = {"passed": True, "evidence_ids": ["smoke-only"], "controls": {}, "diagnostics": {}}
    write_json_atomic(tmp_path / "calibration.json", calibration)
    write_json_atomic(tmp_path / "pilot.json", pilot)
    output = tmp_path / "cli-freeze"
    assert main(["freeze", "--config", str(config), "--out", str(output), "--calibration", str(tmp_path / "calibration.json"),
                 "--pilot", str(tmp_path / "pilot.json")]) == 0
    lock = read_json_checked(output / "protocol.lock.json")
    assert lock["purpose"] == "smoke" and lock["initial_survivors"] == {"0": 8}
