import hashlib
import math

import mpmath as mp
import numpy as np
import pytest
from scipy.integrate import quad


@pytest.mark.parametrize("q", [.01, .1, 1.])
def test_kernel_matches_independent_radial_volume(q):
    from seti_audit.theorem import finite_age_kernel

    h, T, d = .1, 1., 3
    upper = (T + h) / (1 + q)
    radial, _ = quad(lambda r: d * r**(d - 1) * max(0., T + h - (1 + q) * r - max(0., T - r)),
                     0, upper, points=[x for x in (T, h / q) if 0 < x < upper], epsabs=1e-14)
    assert finite_age_kernel(q, h, T, d) / (d + 1) == pytest.approx(radial, rel=1e-9)


def test_kernel_branches_meet_and_tiny_values_survive():
    from seti_audit.theorem import finite_age_kernel

    assert finite_age_kernel(.1, .1, 1, 3) == pytest.approx(.1, rel=1e-14)
    assert finite_age_kernel(np.nextafter(.1, 0), .1, 1, 3) == pytest.approx(.1, rel=1e-14)
    assert finite_age_kernel(1e-13, 1e-12, 1, 3) == pytest.approx(3.7e-12, rel=2e-12)


@pytest.mark.parametrize("alpha", [1, 2])
@pytest.mark.parametrize("h", [.001, .1, .5])
def test_closed_form_power_laws(alpha, h):
    from seti_audit.theorem import continuum_mean

    expected = .75 * h**2 + .5 * h**3 if alpha == 1 else h**3 - .25 * h**4
    assert continuum_mean(h, alpha) == pytest.approx(expected, rel=1e-11)


@pytest.mark.parametrize("alpha", [.5, 1, 2, 3, 4, 6])
def test_repaired_warning_is_derivative_and_has_zero_endpoint(alpha):
    from seti_audit.theorem import continuum_mean, warning_intensity

    h, step = .1, 1e-5
    derivative = (continuum_mean(h - 2 * step, alpha) - 8 * continuum_mean(h - step, alpha)
                  + 8 * continuum_mean(h + step, alpha) - continuum_mean(h + 2 * step, alpha)) / (12 * step)
    assert warning_intensity(h, 0, alpha) == 0
    assert warning_intensity(h, 1, alpha) == pytest.approx(derivative, rel=1e-9)


def test_joint_cdf_conditions_on_arrival_interval_not_exact_arrival():
    from seti_audit.theorem import continuum_mean, warning_intensity, free_joint_cdf

    h, alpha, z, u = .5, 1., .4, .5
    assert free_joint_cdf(h, 1, 1, alpha) == pytest.approx(1, abs=1e-12)
    assert free_joint_cdf(h, 0, 1, alpha) == 0
    assert free_joint_cdf(h, 1, 0, alpha) == 0
    assert free_joint_cdf(h, z, 1, alpha) == pytest.approx(
        -math.expm1(-continuum_mean(z * h, alpha)) / -math.expm1(-continuum_mean(h, alpha)), rel=1e-10)
    at_h = warning_intensity(h, u, alpha) / warning_intensity(h, 1, alpha)
    assert abs(free_joint_cdf(h, 1, u, alpha) - at_h) > .005


def test_atomic_split_counts_each_atom_once_and_cutoff_is_finite():
    from seti_audit.theorem import _atomic_mean, _atomic_warning

    # Unit atom at the split h/T=.1, and the cutoff law q=1.
    assert _atomic_mean(.1, ((.1, 1.),)) == pytest.approx(.025)
    assert _atomic_warning(.1, 1, ((.1, 1.),)) == pytest.approx(1.)
    assert _atomic_mean(.1, ((1., 1.),)) == pytest.approx(.000025)


def test_critical_log_convergence_and_arbitrary_precision():
    from seti_audit.theorem import continuum_mean, leading_mean, high_precision_mean

    ratio = continuum_mean(1e-8, 3) / leading_mean(1e-8, 3)
    assert ratio == pytest.approx(1.03166730608, rel=1e-10)
    assert continuum_mean(1e-12, 3) / leading_mean(1e-12, 3) < ratio
    for alpha in (.5, 1, 2, 3, 4, 6):
        at_80 = high_precision_mean(1e-12, alpha, dps=80)
        at_120 = high_precision_mean(1e-12, alpha, dps=120)
        with mp.workdps(130):
            assert abs(mp.mpf(at_80) / mp.mpf(at_120) - 1) < mp.mpf('1e-60')
        assert continuum_mean(1e-12, alpha) == pytest.approx(float(at_120), rel=1e-10, abs=0)


def test_theorem_check_writes_reproducible_evidence(repo_root, tmp_path):
    from seti_audit.artifacts import read_json_checked
    from seti_audit.cli import main

    source = repo_root / "docs/silence_contact_theorem.pdf"
    assert main(["theorem-check", "--deterministic", "--source", str(source), "--out", str(tmp_path)]) == 0
    result = read_json_checked(tmp_path / "deterministic.json")
    assert result["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result["status"] == "validated"
    assert len(result["ratios"]) == 30  # Six alpha values, four float horizons plus HP 1e-12.
    assert result["warning_derivative_max_relative_error"] < 1e-9
    assert result["precision"]["convergence_relative_tolerance"] == "1e-60"
    assert result["source_scripts_reproduced"] is False
