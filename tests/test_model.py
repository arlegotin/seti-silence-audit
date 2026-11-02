import math

import numpy as np
import pytest


def clocks(births, speeds, gaps=None):
    from seti_audit.contracts import FirstClocks
    v = np.array(speeds, dtype=np.float64)
    return FirstClocks(np.array(births, dtype=np.float64), v,
                       1 / v - 1 if gaps is None else np.array(gaps, dtype=np.float64))


def test_fast_phantom_cannot_expand_or_win_arrival(tiny_geometry):
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[1, 0, 0], [1.1, 0, 0]])
    draw = clocks([0, 1.1], [.1, .9])
    accepted = simulate_history(draw, geometry)
    free = simulate_history(draw, geometry, intersite=False)
    assert free.arrival_year == pytest.approx(2.322222222222222)
    assert accepted.arrival_year == 10
    assert accepted.accepted_indices.tolist() == [0]
    assert accepted.occupation_years[1] == pytest.approx(1)


def test_pre_zero_fast_phantom_does_not_destroy_accepted_survival(tiny_geometry):
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[10, 0, 0], [8, 0, 0]])
    draw = clocks([-100, -50], [.05, .9])
    history = simulate_history(draw, geometry)
    assert history.arrival_year == 100
    assert history.survives and history.arrives_within_horizon
    assert history.accepted_indices.tolist() == [0]
    assert simulate_history(draw, geometry, intersite=False).arrival_year == pytest.approx(-41.11111111111111)


def test_occupation_tie_is_rejected_without_moving_boundary(tiny_geometry):
    from seti_audit.model import simulate_history

    history = simulate_history(clocks([0, 10], [.1, .5]), tiny_geometry([[1, 0, 0], [2, 0, 0]]))
    assert history.accepted_indices.tolist() == [0]
    assert history.diagnostics["flagged_comparisons"]


def test_cancellation_in_old_front_cannot_create_false_century_arrival(tiny_geometry):
    from seti_audit.model import simulate_history

    # Exact front time at the second site is -7.1107e-13 yr, although the
    # binary64 occupation update gives +1.8190e-12 yr after cancellation.
    geometry = tiny_geometry([[1159.5949369500495, -521.2779132462957, -422.23674071951405],
                              [20, 0, 0]])
    history = simulate_history(clocks([-13223.8086358433, 0], [.1, .5]), geometry)
    assert history.accepted_indices.tolist() == [0]
    assert history.survives and not history.arrives_within_horizon
    assert history.arrival_year == pytest.approx(172.73922490067707)


@pytest.mark.parametrize("birth,survives,arrives", [(-10, False, False), (90, True, True), (91, True, False)])
def test_arrival_boundaries(tiny_geometry, birth, survives, arrives):
    from seti_audit.model import simulate_history

    history = simulate_history(clocks([birth], [.1]), tiny_geometry([[1, 0, 0]]))
    assert history.survives is survives
    assert history.arrives_within_horizon is arrives
    assert history.right_censored is (not arrives and survives)


def test_sub_ulp_positive_gap_does_not_turn_late_arrival_into_benchmark_hit(tiny_geometry):
    from seti_audit.model import simulate_history

    history = simulate_history(clocks([0], [np.nextafter(1., 0.)], [1e-18]),
                               tiny_geometry([[100, 0, 0]]))
    assert history.survives
    assert not history.arrives_within_horizon
    assert history.right_censored


def test_no_attempt_is_censored_and_has_no_accepted_sources(tiny_geometry):
    from seti_audit.model import simulate_history

    history = simulate_history(clocks([np.inf], [.1]), tiny_geometry([[1, 0, 0]]))
    assert history.accepted_indices.size == 0
    assert math.isinf(history.arrival_year)
    assert history.survives and not history.arrives_within_horizon and history.right_censored


def test_piecewise_hazard_inverse_including_no_future_births():
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import invert_hazard

    config = ModelConfig(0, 1, 10, "S1", 2)  # One site: lambda=.1, past hazard=1.
    actual = invert_hazard(np.array([.2, 1, 1.4]), config, n_sites=1)
    np.testing.assert_allclose(actual, [-8, 0, 2], atol=1e-14)
    halted = ModelConfig(0, 1, 10, "S1", 0)
    assert np.isinf(invert_hazard(np.array([1.4]), halted, n_sites=1)[0])
    zero = ModelConfig(0, 0, 10, "S1", 10)
    assert np.isinf(invert_hazard(np.array([.2]), zero, n_sites=1)[0])


def test_near_light_speed_support_and_recorded_rounding(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_first_clocks

    class FixedDraws:
        def __init__(self):
            self.values = iter([np.array([.5]), np.array([np.nextafter(0., 1.)])])

        def random(self, size):
            return next(self.values)

    result = sample_first_clocks(ModelConfig(0, 1, 10000, "S4"),
                                 tiny_geometry([[1, 0, 0]]), FixedDraws())
    assert result.speed_gaps[0] > 0
    assert 0 < result.speeds[0] < 1
    assert result.diagnostics["speed_rounding_count"] == 1
    assert result.diagnostics["speed_rounding_mass_bound"] > 0


def test_clock_generation_recovers_exponential_first_attempt_distribution(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_first_clocks

    geometry = tiny_geometry([[1, 0, 0]])
    config = ModelConfig(0, 1, 10, "S1", 0)
    rng = np.random.default_rng(20261101)
    times = np.array([sample_first_clocks(config, geometry, rng).birth_years[0] for _ in range(3000)])
    # P(first birth <= -5) = 1-exp(-.5), independently derived.
    assert abs(np.mean(times <= -5) - 0.3934693402873666) < .04
