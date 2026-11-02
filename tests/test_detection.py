from dataclasses import replace
import math

import numpy as np
import pytest

YEAR_SECONDS = 365.25 * 86400
D = 150 / YEAR_SECONDS


def exact_schedule(pairs=None, site_id="0"):
    from seti_audit.contracts import Scan, Schedule

    pairs = pairs or [(-3 * D, -D)]
    scans = tuple(Scan(f"v{visit}", site_id, scan + 1, start, D, "off-target")
                  for visit, times in enumerate(pairs) for scan, start in enumerate(times))
    return Schedule(scans, (), "exact", "assumed_F2", {}, {"source_status": "synthetic_control"})


def emission(zeta=1, delay=0, lifetime=None, activity="always"):
    from seti_audit.contracts import EmissionConfig
    return EmissionConfig("control", zeta, delay, lifetime, activity)


def detector(low=.8836, high=None, partial=False):
    from seti_audit.contracts import DetectorConfig
    return DetectorConfig("control", low, low if high is None else high, partial)


def test_one_eligible_visit_and_repeated_source_status():
    from seti_audit.detection import source_null_weight

    single = source_null_weight(-30, 1, exact_schedule(), "0", emission(), detector())
    assert single.low == single.high == 1 - .8836
    repeated = source_null_weight(-30, 1, exact_schedule([(-1, -.5), (-.1, -D)]),
                                   "0", emission(zeta=.1), detector())
    assert repeated.low == repeated.high == pytest.approx(1 - .1 * (2 * .8836 - .8836**2))


def test_joint_ctmc_windows_preserve_on_state_and_merge_overlaps():
    from seti_audit.detection import joint_activity

    f, tau, gap = .1, 1 / 365.25, 300 / YEAR_SECONDS
    expected = f * math.exp(-(1 - f) / tau * 2 * D) * (f + (1 - f) * math.exp(-gap / tau))
    assert joint_activity(((0, D), (D + gap, 2 * D + gap)), f, tau) == pytest.approx(expected)
    assert joint_activity(((0, 2 * D), (D, 3 * D)), f, tau) == pytest.approx(
        f * math.exp(-(1 - f) / tau * 3 * D))


def test_and_recovery_bounds_and_directional_gate():
    from seti_audit.detection import pair_recovery_bounds, selection_eligible

    bounds = pair_recovery_bounds(.94)
    assert bounds.low == pytest.approx(.88)
    assert bounds.high == .94
    assert not selection_eligible((1400, 1), 150, (True, False), False)
    assert not selection_eligible((1400, 1), 150, (True, True), True)
    assert selection_eligible((1400, 1), 150, (True, True), False)


@pytest.mark.parametrize("track,admissible", [
    ((1400, 1), True), ((1400, 0), False), ((1400, 8.87), False),
    ((1200, 1), False), ((1341.2005, -8.86), False), ((1150.0005, -8.86), False),
    ((1425, 1), False), ((1530, 1), False), ((1600, 1), False), ((1700, -8.86), True),
])
def test_full_frequency_track_and_fixed_blind_regions(track, admissible):
    from seti_audit.detection import frequency_admissible
    assert frequency_admissible(track, 150) is admissible


def test_retarded_onset_and_finite_lifetime_contain_full_integrations():
    from seti_audit.detection import source_null_weight

    scans = exact_schedule([(-1, -D)])
    # Received emission [-1,0), ON windows also half-open; endpoint equality fits.
    full = source_null_weight(-2, 1, scans, "0", emission(lifetime=1), detector())
    assert full.low == pytest.approx(1 - .8836)
    assert full.rechecks  # Exact temporal boundaries retain their precision audit.
    partial_scans = exact_schedule([(-1 - .5 * D, -D)])
    partial = source_null_weight(-2, 1, partial_scans, "0", emission(lifetime=1), detector())
    assert partial.low == partial.high == 1
    uncal = source_null_weight(-2, 1, partial_scans, "0", emission(lifetime=1), detector(0, 1, True))
    assert (uncal.low, uncal.high) == (0, 1)
    expired = source_null_weight(-4, 1, scans, "0", emission(lifetime=1), detector(0, 1, True))
    assert expired.low == expired.high == 1


def test_no_sources_unobserved_sites_and_incompatible_sources_give_null_one(tiny_geometry):
    from seti_audit.contracts import FirstClocks
    from seti_audit.detection import null_weight, source_null_weight
    from seti_audit.model import simulate_history

    history = simulate_history(FirstClocks(np.array([np.inf]), np.array([.1]), np.array([9.])),
                               tiny_geometry([[1, 0, 0]]))
    assert null_weight(history, tiny_geometry([[1, 0, 0]]), exact_schedule(), emission(), detector()).low == 1
    assert source_null_weight(-30, 1, exact_schedule(site_id="other"), "0", emission(), detector()).low == 1
    assert source_null_weight(-30, 1, exact_schedule(), "0", emission(zeta=0), detector(0, 1, True)).low == 1


def test_cross_source_product_uses_only_accepted_sources(tiny_geometry):
    from seti_audit.contracts import FirstClocks, Scan, Schedule
    from seti_audit.detection import null_weight
    from seti_audit.model import simulate_history

    geometry = tiny_geometry([[1, 0, 0], [2, 0, 0]])
    history = simulate_history(FirstClocks(np.array([-3., -3.]), np.full(2, .1), np.full(2, 9.)), geometry)
    scans = tuple(Scan(f"v{i}", str(i), j + 1, start, D, f"v{1-i}")
                  for i, starts in enumerate([(-4 * D, -2 * D), (-3 * D, -D)])
                  for j, start in enumerate(starts))
    schedule = Schedule(scans, (), "exact", "assumed_F2", {}, {"source_status": "synthetic_control"})
    result = null_weight(history, geometry, schedule, emission(), detector())
    assert result.low == result.high == pytest.approx((1 - .8836)**2)
