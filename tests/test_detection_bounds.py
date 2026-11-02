from dataclasses import replace
from itertools import product
import math

import pytest

from test_detection import D, detector, emission, exact_schedule


def bounded_schedule(intervals=((-1, 0),), repeats=1):
    from seti_audit.contracts import BoundedVisit, Schedule
    visits = tuple(BoundedVisit(f"v{i}", "0", intervals, D) for i in range(repeats))
    return Schedule((), visits, "coarsened_F1", "assumed_F2", {}, {"source_status": "synthetic_control"})


def test_positive_detector_interval_bounds_weights_at_fixed_history():
    from seti_audit.detection import source_null_weight

    schedule = exact_schedule([(-1, -.5), (-.1, -D)])
    bounds = source_null_weight(-30, 1, schedule, "0", emission(), detector(.44, .94))
    low = source_null_weight(-30, 1, schedule, "0", emission(), detector(.94))
    high = source_null_weight(-30, 1, schedule, "0", emission(), detector(.44))
    assert bounds.low == low.low
    assert bounds.high == high.high


def test_repeated_visit_dependence_bounds_average_compatibility_once():
    from seti_audit.detection import source_null_weight

    schedule = exact_schedule([(-1, -.5), (-.1, -D)])
    result = source_null_weight(-30, 1, schedule, "0", emission(zeta=.1), detector(), "robust")
    assert result.low == pytest.approx(.9)
    assert result.high == pytest.approx(1 - .1 * .8836)


def test_bounds_cover_all_schedules_and_shared_efficiencies():
    from seti_audit.detection import source_null_weight

    bounds = source_null_weight(-30, 1, bounded_schedule(repeats=2), "0", emission(zeta=.1), detector(.44, .94))
    for p in (.44, .5, .7, .94):
        for first, second in product(((-.9, -.8), (-.7, -.6), (-.3, -.2)), repeat=2):
            point = source_null_weight(-30, 1, exact_schedule([first, second]), "0", emission(zeta=.1), detector(p))
            assert bounds.low <= point.low <= point.high <= bounds.high
    assert bounds.low == pytest.approx(.9)
    assert bounds.high == pytest.approx(.956)


def test_full_on_packing_impossibility_does_not_imply_partial_response_impossibility():
    from seti_audit.detection import source_null_weight

    schedule = bounded_schedule()
    short = emission(lifetime=D)
    full = source_null_weight(-1.5, 1, schedule, "0", short, detector(.44, .94))
    assert full.low == full.high == 1
    partial = source_null_weight(-1.5, 1, schedule, "0", short, detector(0, 1, True))
    assert (partial.low, partial.high) == (0, 1)


def test_unknown_gap_ctmc_bounds_use_exact_on_durations():
    from seti_audit.detection import source_null_weight

    b = .9 * 365.25
    result = source_null_weight(-30, 1, bounded_schedule(), "0", emission(activity="ctmc"), detector(.44, .94))
    assert result.low == pytest.approx(1 - .94 * .1 * math.exp(-b * 2 * D))
    assert result.high == pytest.approx(1 - .44 * .1**2 * math.exp(-b * 2 * D))


def test_future_replay_leaves_every_past_likelihood_unchanged(tiny_geometry):
    import numpy as np
    from seti_audit.contracts import FirstClocks, FutureMarks, ModelConfig
    from seti_audit.detection import null_weight
    from seti_audit.model import simulate_history, replay_future

    geometry = tiny_geometry([[10, 0, 0], [20, 0, 0]])
    prefix = simulate_history(FirstClocks(np.array([-50., np.inf]), np.full(2, .1), np.full(2, 9.)), geometry)
    config = ModelConfig(0, 1, 1000, "S3")
    marks = FutureMarks(np.array([np.inf, .05]), np.array([.1, .9]), np.array([9., 1/.9-1]))
    first = exact_schedule([(-4 * D, -2 * D)])
    second = exact_schedule([(-3 * D, -D)], site_id="1")
    schedule = replace(first, exact_scans=first.exact_scans + tuple(
        replace(s, visit_id="second") for s in second.exact_scans))
    for e in (emission(), emission(zeta=.1), emission(delay=100), emission(lifetime=100), emission(activity="ctmc")):
        expected = null_weight(prefix, geometry, schedule, e, detector())
        for k in (0, 1, 10):
            assert null_weight(replay_future(prefix, config, geometry, marks, k), geometry, schedule, e, detector()) == expected
