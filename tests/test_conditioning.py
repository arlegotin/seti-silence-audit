from collections import Counter
from itertools import product
import json
import math

import numpy as np
import pytest


def test_finite_support_survival_subset_and_conditional_law(repo_root, tiny_geometry):
    from test_enumeration import independent_accepted_sites
    from seti_audit.contracts import FirstClocks
    from seti_audit.model import simulate_history

    fixture = json.loads((repo_root / "tests/fixtures/finite_histories.json").read_text())
    positions = np.array(fixture["positions_ly"])
    geometry = tiny_geometry([[x, 0, 0] for x in positions])
    support = [np.inf if t is None else t for t in fixture["birth_support_years"]]
    direct, proposal = Counter(), Counter()
    free_survival_is_stronger = False
    for times in product(support, repeat=3):
        for velocities in product(fixture["speed_support"], repeat=3):
            key = times + velocities
            accepted = independent_accepted_sites(times, velocities, positions)
            arrival = min((times[i] + positions[i] / velocities[i] for i in accepted), default=np.inf)
            survives = arrival > 0
            lower_cone = all(t + r / .1 > 0 for t, r in zip(times, positions))
            assert not survives or lower_cone
            model = simulate_history(FirstClocks(np.array(times), np.array(velocities),
                                                 1 / np.array(velocities) - 1), geometry)
            assert model.survives == survives
            if survives:
                direct[key] = 1
                free_survival_is_stronger |= min(t + r / v for t, r, v in zip(times, positions, velocities)) <= 0
            if lower_cone and survives:
                proposal[key] = 1
    assert free_survival_is_stronger
    assert direct == proposal
    for state in direct:
        assert direct[state] / direct.total() == proposal[state] / proposal.total()


@pytest.mark.parametrize("mode,expected", [("lower_cone", -50), ("ideal_silence", 40)])
def test_conditional_clock_includes_original_hazard_offset(tiny_geometry, mode, expected):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_first_clocks

    class FixedUniform:
        def random(self, size):
            return np.full(size, math.exp(-.05))

    config = ModelConfig(0, 1, 1000, "S1", 1)
    draw = sample_first_clocks(config, tiny_geometry([[10, 0, 0]]), FixedUniform(), mode)
    assert draw.birth_years[0] == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize("speed,q", [("S1", 9), ("S2", 1)])
def test_common_speed_proposals_survive_without_rejection(tiny_geometry, speed, q):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_surviving_prefix, survival_constant, survival_diagnostic

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0]])
    config = ModelConfig(0, 3, 1000, speed)
    rng = np.random.default_rng(20261101)
    for _ in range(30):
        prefix, attempts = sample_surviving_prefix(config, geometry, rng)
        assert attempts == 1 and prefix.survives
        assert all(t <= 0 or np.isinf(t) for t in prefix.birth_years)
    expected_c = math.exp(-.0015 * sum(1000 - r * (1 + q) for r in (10, 20)))
    assert survival_constant(config, geometry) == pytest.approx(expected_c)
    assert survival_diagnostic(config, geometry, rng, n_proposals=37) == (37, 37, pytest.approx(expected_c))


def test_low_rate_conditional_sampler_matches_unconditional_rejection(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_first_clocks, sample_surviving_prefix, simulate_history

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0], [30, 0, 0]])
    config = ModelConfig(0, .5, 1000, "S4")
    ordinary, proposed = [], []
    rng_direct = np.random.default_rng([20261101, 0, 5, 0])
    rng_proposal = np.random.default_rng([20261101, 0, 5, 1])
    while len(ordinary) < 1500:
        prefix = simulate_history(sample_first_clocks(config, geometry, rng_direct, horizon_years=0), geometry)
        if prefix.survives:
            ordinary.append(prefix.arrives_within_horizon)
    for _ in range(1500):
        prefix, _ = sample_surviving_prefix(config, geometry, rng_proposal)
        proposed.append(prefix.arrives_within_horizon)
    assert abs(np.mean(ordinary) - np.mean(proposed)) < .08
