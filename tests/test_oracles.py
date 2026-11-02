from dataclasses import replace
from itertools import product
import math

import numpy as np
import pytest

from test_detection import D, detector, emission, exact_schedule
from test_detection_bounds import bounded_schedule


def test_no_birth_control_is_analytic_zero(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    result = independent_oracle(ModelConfig(0, 0, 1000, "S4"), tiny_geometry([[10, 0, 0]]),
                                exact_schedule(), emission(), detector())
    assert result.C == 1
    assert result.likelihood.low == result.likelihood.high == 1
    assert result.R0.low == result.R0.high == result.R.low == result.R.high == 0


@pytest.mark.parametrize("speed,expected_c", [("S1", math.exp(-.9)), ("S2", math.exp(-.98))])
def test_one_site_first_clock_and_no_birth_atom(tiny_geometry, speed, expected_c):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    result = independent_oracle(ModelConfig(0, 1, 1000, speed), tiny_geometry([[10, 0, 0]]),
                                exact_schedule(), emission(zeta=0), detector())
    assert result.C == pytest.approx(expected_c, rel=1e-10)
    expected_risk = -math.expm1(-.1)
    assert result.R0.low <= expected_risk <= result.R0.high
    assert result.R.low <= expected_risk <= result.R.high
    assert result.likelihood.low == result.likelihood.high == 1


def test_uniform_q_analytic_survival_and_future_invariance(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    config = ModelConfig(0, 1, 1000, "S4")
    geometry = tiny_geometry([[10, 0, 0]])
    results = [independent_oracle(replace(config, future_multiplier=k), geometry,
                                  exact_schedule(), emission(), detector()) for k in (0, 1, 10)]
    expected_c = math.exp(-.99) * math.expm1(.01) / .01
    for result in results:
        assert result.C == pytest.approx(expected_c, rel=1e-10)
        assert result.likelihood.low == pytest.approx(results[0].likelihood.low, abs=1e-10)
    assert results[1].R0.low <= -math.expm1(-.1) <= results[1].R0.high
    assert results[0].R0.high < results[1].R0.low < results[2].R0.low


def test_full_on_selection_has_known_one_site_update(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    result = independent_oracle(ModelConfig(0, 1, 1000, "S1"), tiny_geometry([[10, 0, 0]]),
                                exact_schedule(), emission(), detector(1))
    expected_likelihood = math.exp(-.001 * (90 - 3 * D))
    expected_risk = -math.expm1(-.001 * (10 + 3 * D))
    assert result.likelihood.low <= expected_likelihood <= result.likelihood.high
    assert result.R.low <= expected_risk <= result.R.high
    assert result.R.high < result.R0.low


def test_independent_products_match_finite_support_enumeration():
    from seti_audit.oracles import independent_product_summary

    supports = [((.2, -1, .1), (.4, 50, .2), (.4, 200, 1)),
                ((.1, -1, 1), (.2, 20, .6), (.7, math.inf, 1))]
    C = G = H = K = 0.
    for first, second in product(*supports):
        probability = first[0] * second[0]
        arrival = min(first[1], second[1])
        weight = first[2] * second[2]
        if arrival > 0:
            C += probability
            G += probability * weight
        if arrival > 100:
            H += probability
            K += probability * weight
    result = independent_product_summary(np.array([.8, .9]), np.array([.4, .7]),
                                         np.array([[.48, .48], [.82, .82]]),
                                         np.array([[.4, .4], [.7, .7]]))
    assert result.C == pytest.approx(C)
    assert result.likelihood.low == pytest.approx(G / C)
    assert result.R0.low == pytest.approx(1 - H / C)
    assert result.R.low == pytest.approx(1 - K / G)


def test_interval_oracle_covers_finite_shared_detector_cases(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    config = ModelConfig(0, 1, 1000, "S4")
    geometry = tiny_geometry([[10, 0, 0]])
    outer = independent_oracle(config, geometry, bounded_schedule(), emission(), detector(.44, .94))
    for p in (.44, .55, .7, .94):
        point = independent_oracle(config, geometry, exact_schedule([(-.8, -.2)]), emission(), detector(p))
        assert outer.R.low <= point.R.low <= point.R.high <= outer.R.high
    assert max(outer.absolute_errors.values()) < 1e-4


def test_oracle_uses_unconditional_clocks_and_independent_numerical_checks(repo_root, tmp_path, monkeypatch):
    from seti_audit.contracts import load_protocol
    from seti_audit.data import load_catalog, load_schedule
    import seti_audit.model as model
    from seti_audit.oracles import independent_oracle

    def forbidden(*args, **kwargs):
        raise AssertionError("Independent oracle must never consume a conditional proposal sampler")

    monkeypatch.setattr(model, "sample_first_clocks", forbidden)
    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    config = next(m for m in protocol.models if m.mu == 12 and m.speed_id == "S4" and m.age_years == 10000)
    result = independent_oracle(config, catalog.geometry, schedule, protocol.emissions[1], protocol.detectors[0])
    assert result.R0.low <= -math.expm1(-.12) <= result.R0.high
    assert max(result.absolute_errors.values()) < 1e-4
    assert result.validation["methods"] == ["analytic_affine", "split_quad"]
    assert result.validation["max_method_disagreement"] < 1e-8
    assert result.status == "validated"


def test_unconditional_independent_mc_checks_original_clock_integral(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import independent_oracle

    # Independent vectorized first clocks, with this model's own conditioning.
    # No accepted-history sampler or production likelihood is used here.
    config = ModelConfig(0, 1, 1000, "S4")
    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0]])
    rng = np.random.default_rng([20261101, 7, 1])
    births = -1000 + rng.exponential(2000, size=(150000, 2))
    arrivals = births + geometry.radii_ly * (1 + rng.random(births.shape))
    survives = np.min(arrivals, axis=1) > 0
    century = np.min(arrivals, axis=1) <= 100
    weights = np.where(births[:, 0] + 10 <= -3 * D, 1 - .8836, 1.)
    ell = np.mean(weights[survives])
    risk = np.sum(weights[survives] * century[survives]) / np.sum(weights[survives])
    result = independent_oracle(config, geometry, exact_schedule(), emission(), detector())
    assert abs(result.C - np.mean(survives)) < .005
    assert abs(result.likelihood.low - ell) < .005
    assert abs(result.R.low - risk) < .005
