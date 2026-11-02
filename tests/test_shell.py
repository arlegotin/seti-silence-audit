import math

import numpy as np
import pytest
from scipy.stats import beta


def test_positive_poisson_uses_exact_conditional_cdf_without_rare_rejection():
    from seti_audit.theorem import _positive_poisson

    p1 = .25 / math.expm1(.25)
    p2 = p1 * .25 / 2
    assert _positive_poisson(.25, p1 - 1e-10) == 1
    assert _positive_poisson(.25, p1 + 1e-10) == 2
    assert _positive_poisson(.25, p1 + p2 + 1e-10) == 3
    assert [_positive_poisson(.25, u) for u in (.1, .9, .999, .99999)] == [1, 2, 3, 5]
    assert _positive_poisson(.25, np.nextafter(1., 0.)) > 8
    with pytest.raises(ValueError):
        _positive_poisson(0, .5)
    with pytest.raises(ValueError):
        _positive_poisson(.1, 1.)


def test_forced_phantom_changes_contact_winner_preserves_first_signal():
    from seti_audit.theorem import _evaluate_shell

    points = np.array([[1., 0, 0, 0, 9.], [1.1, 0, 0, 1.1, 1 / .9 - 1]])
    result = _evaluate_shell(points, h=20.)
    assert result["accepted_indices"] == [0]
    assert result["free_arrival_delay"] == pytest.approx(1.3222222222222224)
    assert result["arrival_delay"] == 9
    assert result["first_accepted_signal_delay"] == result["first_potential_signal_delay"] == 0
    assert result["suppressed_count"] == 1


def test_shell_right_censoring_does_not_report_global_late_contact():
    from seti_audit.theorem import _evaluate_shell

    result = _evaluate_shell(np.array([[1., 0, 0, .1, 9.]]), h=.5)
    assert result["right_censored"] is True
    assert result["arrival_delay"] is None
    assert result["accepted_warning_fraction"] is None
    assert result["free_arrival_delay"] > .5


def test_forced_phantom_inside_confirmatory_shell_support():
    from seti_audit.theorem import _evaluate_shell

    points = np.array([[1., 0, 0, .05, .9], [.9, 0, 0, .25, .01]])
    assert np.all((points[:, 4] > 0) & (points[:, 4] < 1))
    signals = np.linalg.norm(points[:, :3], axis=1) + points[:, 3]
    assert np.all((signals > 1) & (signals < 1.5))
    result = _evaluate_shell(points, h=.5)
    assert result["free_arrival_delay"] == pytest.approx(.159)
    assert result["suppressed_count"] == 1
    assert result["accepted_indices"] == [0]
    assert result["right_censored"] is True
    assert result["first_potential_signal_delay"] == result["first_accepted_signal_delay"]


@pytest.mark.parametrize("h", [.02, .5])
def test_restricted_shell_matches_finite_horizon_free_law_and_rigorous_bounds(tmp_path, h):
    from seti_audit.resources import ResourceLedger
    from seti_audit.theorem import sample_shell, free_joint_cdf

    ledger = ResourceLedger(tmp_path / "resources.jsonl")
    result = sample_shell({"alpha": 1, "h": h, "phase": "development"},
                          np.random.default_rng([20261101, 0, 9, int(h * 100)]), 2000, ledger)
    assert result.trials == 2000
    assert result.contact_count + result.censored_count == result.trials
    assert len(result.free_horizon_fractions) == len(result.free_warning_fractions) == 2000
    for z, u in ((.4, 1.), (1., .5), (.8, .7)):
        empirical = np.mean((result.free_horizon_fractions <= z) & (result.free_warning_fractions <= u))
        assert abs(empirical - free_joint_cdf(h, z, u, 1)) < .06
    n, k = result.trials, result.contact_count
    lo = 0 if k == 0 else beta.ppf(.0005, k, n - k + 1)
    hi = 1 if k == n else beta.ppf(.9995, k + 1, n - k)
    free_p = -math.expm1(-result.b)
    assert free_p * hi >= result.b * math.exp(-result.s)
    assert free_p * lo <= free_p
    assert result.resource_use["point_proposals"] >= result.trials
    assert ledger.usage()["history_evaluations"] == 2000
    assert ledger.pending_jobs() == []


def test_shell_rejects_unvalidated_parameter_extrapolation(tmp_path):
    from seti_audit.theorem import sample_shell
    from seti_audit.resources import ResourceLedger

    with pytest.raises(ValueError, match="alpha=1"):
        sample_shell({"alpha": 3, "h": .5}, np.random.default_rng(0), 1,
                     ResourceLedger(tmp_path / "resources.jsonl"))


def test_shell_cli_preserves_phase_and_integer_joint_counts(repo_root, tmp_path):
    from seti_audit.artifacts import read_json_checked
    from seti_audit.cli import main

    assert main(["theorem-check", "--shell", "--histories", "20", "--out", str(tmp_path),
                 "--source", str(repo_root / "docs/silence_contact_theorem.pdf")]) == 0
    result = read_json_checked(tmp_path / "shell-development.json")
    assert result["phase"] == "development"
    assert len(result["horizons"]) == 2
    for row in result["horizons"]:
        assert row["trials"] == 20
        assert all(isinstance(cell["count"], int) and 0 <= cell["count"] <= 20
                   for cell in row["free_joint_counts"])
