from itertools import product

import numpy as np
import pytest


def independent_accepted_sites(births, velocities, positions):
    """Finite-support oracle using direct ball coverage, not occupation updates."""
    accepted = []
    for i in sorted(range(len(births)), key=lambda j: (births[j], str(j))):
        if births[i] > 100 or not np.isfinite(births[i]):
            continue
        covered = any(abs(positions[i] - positions[j]) <= velocities[j] * (births[i] - births[j])
                      for j in accepted)
        if not covered:
            accepted.append(i)
    return accepted


def test_finite_support_matches_independent_coverage_oracle(tiny_geometry):
    from seti_audit.contracts import FirstClocks
    from seti_audit.model import simulate_history

    positions = np.array([1., 2., 3.])
    geometry = tiny_geometry([[x, 0, 0] for x in positions])
    tested = 0
    for births in product((-20., -5., 0.), repeat=3):
        for speeds in product((.1, .5), repeat=3):
            velocities = np.array(speeds)
            draw = FirstClocks(np.array(births), velocities, 1 / velocities - 1)
            expected = independent_accepted_sites(births, velocities, positions)
            result = simulate_history(draw, geometry)
            assert result.accepted_indices.tolist() == expected
            tested += 1
    assert tested == 216


@pytest.mark.parametrize("speed", [.1, .5])
def test_common_speed_accepted_and_potential_first_arrivals_agree_pathwise(tiny_geometry, speed):
    from seti_audit.contracts import FirstClocks
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[1, 0, 0], [2, 0, 0], [-3, 0, 0]])
    for births in product((-20., -5., 0.), repeat=3):
        v = np.full(3, speed)
        draw = FirstClocks(np.array(births), v, 1 / v - 1)
        assert simulate_history(draw, geometry).arrival_year == pytest.approx(
            simulate_history(draw, geometry, intersite=False).arrival_year, abs=1e-12)
