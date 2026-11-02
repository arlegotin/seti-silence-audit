import numpy as np
import pytest


def prefix_control(tiny_geometry):
    from seti_audit.contracts import FirstClocks
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[10, 0, 0], [8, 0, 0], [20, 0, 0]])
    speeds = np.array([.1, .9, .1])
    prefix = simulate_history(FirstClocks(np.array([-50, -25, np.inf]), speeds, 1 / speeds - 1), geometry)
    return geometry, prefix


def test_future_replays_keep_past_suppression_and_shared_marks(tiny_geometry):
    from seti_audit.contracts import FutureMarks, ModelConfig
    from seti_audit.model import replay_future

    geometry, prefix = prefix_control(tiny_geometry)
    config = ModelConfig(0, 1, 1000, "S3")
    speeds = np.array([.1, .1, .9])
    marks = FutureMarks(np.array([np.inf, np.inf, .05]), speeds, 1 / speeds - 1)
    histories = {k: replay_future(prefix, config, geometry, marks, k) for k in (0, 1, 10)}
    assert histories[0].accepted_indices.tolist() == [0]
    assert histories[1].accepted_indices.tolist() == [0]
    assert histories[10].accepted_indices.tolist() == [0, 2]
    assert histories[10].birth_years[2] == pytest.approx(15)
    for history in histories.values():
        assert history.birth_years[1] == -25  # Rejected old candidate never receives another attempt.
        assert history.survives == prefix.survives
        assert history.accepted_indices[0] == prefix.accepted_indices[0]
    np.testing.assert_array_equal(marks.residual_hazards, [np.inf, np.inf, .05])
    np.testing.assert_array_equal(prefix.birth_years, [-50, -25, np.inf])


def test_new_residual_clocks_only_belong_to_unattempted_sites(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_future_marks

    _, prefix = prefix_control(tiny_geometry)
    marks = sample_future_marks(prefix, ModelConfig(0, 1, 1000, "S3"), np.random.default_rng(9))
    assert np.isinf(marks.residual_hazards[0]) and np.isinf(marks.residual_hazards[1])
    assert np.isfinite(marks.residual_hazards[2]) and marks.residual_hazards[2] > 0


def test_future_rate_cannot_be_negative(tiny_geometry):
    from seti_audit.contracts import FutureMarks, ModelConfig
    from seti_audit.model import replay_future

    geometry, prefix = prefix_control(tiny_geometry)
    marks = FutureMarks(np.array([np.inf, np.inf, .05]), np.full(3, .1), np.full(3, 9.))
    with pytest.raises(ValueError):
        replay_future(prefix, ModelConfig(0, 1, 1000, "S3"), geometry, marks, -1)
