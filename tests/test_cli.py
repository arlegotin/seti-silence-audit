from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("command", ["env", "acquire", "validate-data", "theorem-check", "calibrate", "pilot", "freeze", "run", "report", "smoke", "check"])
def test_required_subcommand_parsers_are_installed(command):
    result = subprocess.run([sys.executable, "-m", "seti_audit", command, "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_offline_smoke_completes_history_likelihood_interval_and_report(repo_root, tmp_path):
    from seti_audit.cli import main
    from seti_audit.artifacts import read_json_checked

    output = tmp_path / "smoke"
    assert main(["smoke", "--config", str(repo_root / "config/protocol.json"), "--out", str(output)]) == 0
    row = read_json_checked(output / "results/model_rows.json")["rows"][0]
    assert row["completion_status"] != "pending"
    assert row["surviving"] == 1
    assert row["protocol_hash"]
    assert "synthetic" in (output / "report/REPORT.md").read_text().lower()
    assert main(["report", "--protocol", str(output / "results/protocol.lock.json"), "--from-results"]) == 0


def test_missing_report_input_is_blocking_input_not_success(tmp_path):
    from seti_audit.cli import main

    assert main(["report", "--protocol", str(tmp_path / "missing.json"), "--from-results"]) == 3


def test_selected_checks_do_not_certify_full_correctness(tmp_path):
    from seti_audit.experiments import verify_correctness
    from seti_audit.resources import ResourceLedger

    selected = tmp_path / "test_tiny.py"
    selected.write_text("def test_known_answer():\n    assert 2 + 3 == 5\n")
    result = verify_correctness(tmp_path / "correctness.json", ResourceLedger(tmp_path / "usage.jsonl"), test_paths=(str(selected),))
    assert result["status"] == "passed" and result["scope"] == "selected"
    assert result["test_count"] == 1


def test_standalone_shell_does_not_claim_unregistered_confirmation(repo_root, tmp_path):
    from seti_audit.cli import main

    assert main(["theorem-check", "--source", str(repo_root / "docs/silence_contact_theorem.pdf"),
                 "--out", str(tmp_path), "--shell", "--histories", "1", "--phase", "confirmation"]) == 2
