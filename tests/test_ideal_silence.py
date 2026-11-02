from itertools import product
import math

import numpy as np
import pytest


def test_ideal_void_probability_is_speed_independent(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.oracles import ideal_silence_probability, ideal_silence_gap

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0]])
    for speed in ("S1", "S2", "S3", "S4"):
        assert ideal_silence_probability(ModelConfig(0, 2, 1000, speed), geometry) == pytest.approx(math.exp(-1.97))
    assert ideal_silence_gap(geometry, .1) == 90


def test_accepted_and_potential_silence_agree_in_exhaustive_control(tiny_geometry):
    from seti_audit.contracts import FirstClocks
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0], [30, 0, 0]])
    for births in product((-50, -15, 0), repeat=3):
        for speeds in product((.1, .5), repeat=3):
            v = np.array(speeds)
            history = simulate_history(FirstClocks(np.array(births), v, 1 / v - 1), geometry)
            potential = min(np.array(births) + geometry.radii_ly) > 0
            accepted = min((births[i] + geometry.radii_ly[i] for i in history.accepted_indices), default=math.inf) > 0
            assert potential == accepted


def test_direct_ideal_sampler_obeys_discrete_gap_and_one_site_law(tiny_geometry):
    from seti_audit.contracts import ModelConfig
    from seti_audit.model import sample_first_clocks, simulate_history
    from seti_audit.oracles import ideal_silence_gap

    geometry = tiny_geometry([[10, 0, 0]])
    config = ModelConfig(0, 100, 1000, "S1")  # Synthetic lambda=.1, ideal gap=90.
    rng = np.random.default_rng([20261101, 0, 7])
    hits = 0
    for _ in range(3000):
        history = simulate_history(sample_first_clocks(config, geometry, rng, "ideal_silence"), geometry)
        assert history.arrival_year >= ideal_silence_gap(geometry, .1)
        hits += int(history.arrives_within_horizon)
    assert abs(hits / 3000 - .6321205588285577) < .04
