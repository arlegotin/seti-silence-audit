from itertools import product

import numpy as np
import pytest


def assert_same_history(actual, expected):
    np.testing.assert_array_equal(actual.accepted_indices, expected.accepted_indices)
    np.testing.assert_array_equal(actual.occupation_years, expected.occupation_years)
    assert actual.arrival_year == expected.arrival_year
    assert actual.survives == expected.survives
    assert actual.arrives_within_horizon == expected.arrives_within_horizon
    assert actual.right_censored == expected.right_censored


@pytest.mark.parametrize("intersite", [True, False])
def test_batch_equals_scalar_on_all_finite_support_states(tiny_geometry, intersite):
    from seti_audit.contracts import ClockBatch, FirstClocks
    from seti_audit.model import simulate_batch, simulate_history, history_at

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0], [30, 0, 0]])
    states = list(product(product((-200., -50., 0., np.inf), repeat=3), product((.1, .5), repeat=3)))
    births, speeds = (np.array([s[i] for s in states]) for i in (0, 1))
    clocks = ClockBatch(births, speeds, 1 / speeds - 1)
    batch = simulate_batch(clocks, geometry, intersite=intersite)
    for index in range(len(states)):
        expected = simulate_history(FirstClocks(births[index], speeds[index], 1 / speeds[index] - 1), geometry, intersite)
        assert_same_history(history_at(batch, index), expected)


def test_batch_precision_fallback_handles_phantom_and_subulp_boundary(tiny_geometry):
    from seti_audit.contracts import ClockBatch, FirstClocks
    from seti_audit.model import simulate_batch, simulate_history, history_at

    geometry = tiny_geometry([[1000000., 0, 0], [1000000.1, 0, 0]])
    births = np.array([[-10000000.1, -10000000.1 + 1], [99.999999999999, np.inf]])
    q = np.array([[9., .01], [9., 9.]])
    speeds = 1 / (1 + q)
    clocks = ClockBatch(births, speeds, q)
    batch = simulate_batch(clocks, geometry)
    for i in range(2):
        assert_same_history(history_at(batch, i), simulate_history(FirstClocks(births[i], speeds[i], q[i]), geometry))


def test_ties_use_site_ids_and_partial_microbatches_preserve_results(tiny_geometry):
    from seti_audit.contracts import ClockBatch, Geometry, FirstClocks
    from seti_audit.model import simulate_batch, simulate_history, history_at, simulate_microbatches

    raw = tiny_geometry([[1., 0, 0], [1., 0, 0], [2., 0, 0]])
    geometry = Geometry(("2", "10", "1"), raw.xyz_ly, raw.radii_ly, raw.distances_ly)
    clocks = ClockBatch(np.zeros((7, 3)), np.full((7, 3), .1), np.full((7, 3), 9.))
    whole = simulate_batch(clocks, geometry)
    small = simulate_microbatches(clocks, geometry, available_bytes=2 * 3 * 128)
    for i in range(7):
        assert_same_history(history_at(whole, i), history_at(small, i))
    assert_same_history(history_at(whole, 0), simulate_history(FirstClocks(np.zeros(3), np.full(3, .1), np.full(3, 9.)), geometry))
    assert whole.accepted_mask[0].tolist() == [False, True, True]


def test_batched_conditional_clocks_keep_offset_and_scalar_path(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol, FirstClocks
    from seti_audit.data import load_catalog
    from seti_audit.model import sample_clock_batch, simulate_batch, simulate_history, history_at

    protocol = load_protocol(repo_root / "config/protocol.json")
    geometry = load_catalog(repo_root / "docs/blueprint.md", tmp_path).geometry
    for config in (protocol.models[0], protocol.models[12], protocol.models[14], protocol.models[15]):
        clocks = sample_clock_batch(config, geometry, np.random.default_rng([20261101, 0, 11, config.model_id]),
                                    67, conditioning="lower_cone", horizon_years=0)
        floor_inverse = 10 if config.speed_id in ("S1", "S3") else 2
        assert np.all(clocks.birth_years >= np.maximum(-config.age_years, -geometry.radii_ly * floor_inverse))
        batch = simulate_batch(clocks, geometry)
        for i in range(67):
            expected = simulate_history(FirstClocks(clocks.birth_years[i], clocks.speeds[i], clocks.speed_gaps[i]), geometry)
            assert_same_history(history_at(batch, i), expected)
        if config.speed_id == "S1":
            assert np.all(batch.survives)


def test_batch_f1_weights_match_scalar_for_all_emissions_and_detectors(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.detection import batch_null_weights, null_weight
    from seti_audit.model import sample_clock_batch, simulate_batch, history_at

    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    clocks = sample_clock_batch(protocol.models[12], catalog.geometry, np.random.default_rng(11), 19, "lower_cone")
    batch = simulate_batch(clocks, catalog.geometry)
    for emission in protocol.emissions:
        for detector in protocol.detectors:
            low, high, diagnostics = batch_null_weights(batch, catalog.geometry, schedule, emission, detector)
            for i in range(19):
                scalar = null_weight(history_at(batch, i), catalog.geometry, schedule, emission, detector)
                assert low[i] == pytest.approx(scalar.low, abs=2e-14)
                assert high[i] == pytest.approx(scalar.high, abs=2e-14)


def test_batch_rechecks_original_cancellation_and_subulp_cases(tiny_geometry):
    from seti_audit.contracts import ClockBatch
    from seti_audit.model import simulate_batch, history_at

    geometry = tiny_geometry([[1159.5949369500495, -521.2779132462957, -422.23674071951405], [20, 0, 0]])
    batch = simulate_batch(ClockBatch(np.array([[-13223.8086358433, 0.]]), np.array([[.1, .5]]), np.array([[9., 1.]])), geometry)
    assert history_at(batch, 0).accepted_indices.tolist() == [0]
    assert not batch.arrives_within_horizon[0]
    assert batch.diagnostics["scalar_rechecks"]
    tiny = simulate_batch(ClockBatch(np.array([[0.]]), np.array([[np.nextafter(1., 0.)]]), np.array([[1e-18]])),
                          tiny_geometry([[100., 0, 0]]))
    assert tiny.right_censored[0] and not tiny.arrives_within_horizon[0]


def test_batch_selection_rechecks_emission_boundary(tiny_geometry):
    from seti_audit.contracts import ClockBatch
    from seti_audit.model import simulate_batch, history_at
    from seti_audit.detection import batch_null_weights, null_weight
    from test_detection import emission, detector
    from test_detection_bounds import bounded_schedule

    geometry = tiny_geometry([[1., 0, 0]])
    clocks = ClockBatch(np.array([[-2.], [-2. + 5e-13], [-2. - 5e-13]]), np.full((3, 1), .1), np.full((3, 1), 9.))
    batch = simulate_batch(clocks, geometry)
    schedule, e, d = bounded_schedule(), emission(lifetime=1), detector()
    low, high, diagnostic = batch_null_weights(batch, geometry, schedule, e, d)
    assert diagnostic["source_precision_rechecks"] == 3
    for i in range(3):
        scalar = null_weight(history_at(batch, i), geometry, schedule, e, d)
        assert low[i] == scalar.low and high[i] == scalar.high
