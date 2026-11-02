from copy import deepcopy

import numpy as np
import pytest

from test_inference import point_lock


def test_threshold_equality_is_retained_and_strict_upper_exclusion():
    from seti_audit.contracts import WeightBounds
    from seti_audit.inference import compatibility

    assert compatibility(WeightBounds(.05, .05), .05) == "retained"
    assert compatibility(WeightBounds(.04, .049999), .05) == "excluded"
    assert compatibility(WeightBounds(.04, .05), .05) == "unresolved"


@pytest.mark.parametrize("baseline,post,retained,expected", [
    ((.2, .22), (.1, .14), True, "material"),
    ((.09, .11), (.085, .095), True, "nonmaterial"),  # Relative negative.
    ((.02, .022), (.013, .019), True, "nonmaterial"),  # Absolute negative.
    ((.09, .11), (.04, .095), True, "inconclusive"),
    ((.09, .11), (.085, .095), False, "inconclusive"),
    ((0., .1), (0., .01), True, "inconclusive"),
    ((0., 0.), (0., .01), True, "nonmaterial"),
])
def test_positive_and_negative_certificates_have_distinct_inequalities(baseline, post, retained, expected):
    from seti_audit.contracts import WeightBounds
    from seti_audit.inference import certify_narrowing

    assert certify_narrowing(WeightBounds(*baseline), WeightBounds(*post), retained) == expected


def test_unresolved_missing_high_risk_cell_blocks_false_positive():
    from seti_audit.inference import summarize

    lock = point_lock()
    first = lock["cells"][0]
    first["deterministic"] = {"C": [1., 1.], "likelihood": [.9, .9], "R0": [.3, .3], "R": [.1, .1]}
    second = deepcopy(first)
    second.update(cell_id="missing", baseline_id="other")
    del second["deterministic"]
    lock["cells"].append(second)
    result = summarize({}, lock, {})
    assert result.certificates["bright"]["0.05"] == "inconclusive"
    assert result.envelopes["bright"]["0.05"]["Ipost"] == [0., 1.]
    assert result.certified["bright"]["0.05"] == ["c"]
    assert result.possible["bright"]["0.05"] == ["c", "missing"]


def test_empty_possible_family_is_incompatible_without_zero_risk():
    from seti_audit.inference import summarize

    lock = point_lock()
    lock["cells"][0]["deterministic"] = {"C": [1., 1.], "likelihood": [0., .001], "R0": [.3, .3], "R": [.1, .1]}
    result = summarize({}, lock, {})
    assert result.certificates["bright"]["0.05"] == "incompatible"
    assert result.envelopes["bright"]["0.05"]["Ipost"] is None


def test_invisible_counterparts_analytically_preclude_full_family_contraction():
    from seti_audit.inference import summarize

    lock = point_lock()
    first = lock["cells"][0]
    first["deterministic"] = {"C": [1., 1.], "likelihood": [.9, .9], "R0": [0., 1.], "R": [.1, .1]}
    dark = deepcopy(first)
    dark.update(cell_id="dark", analytic_unit_weight=True)
    del dark["deterministic"]
    lock["cells"].append(dark)
    result = summarize({}, lock, {})
    assert result.certificates["bright"]["0.05"] == "nonmaterial"
    assert result.envelopes["bright"]["0.05"]["analytic_obstruction"] == "unit_weight_counterparts"


def test_shared_registry_cannot_silently_reuse_conflicting_samples():
    from seti_audit.inference import accumulate, summarize

    lock = point_lock()
    second = deepcopy(lock["cells"][0]); second["cell_id"] = "second"; lock["cells"].append(second)
    counts = accumulate(np.array([True, False]), np.ones(2), np.array([.2, .8]))
    other = accumulate(np.array([False, False]), np.ones(2), np.array([.2, .8]))
    with pytest.raises(ValueError, match="shared interval"):
        summarize({"c": counts, "second": other}, lock, {q: 1 for q in ("R0", "likelihood", "R")})


def test_invalid_deterministic_evidence_keeps_conservative_outer_interval():
    from seti_audit.inference import summarize

    lock = point_lock()
    lock["cells"][0]["deterministic"] = {"status": "needs_precision", "C": [1., 1.],
                                       "likelihood": [.9, .9], "R0": [.3, .3], "R": [.1, .1]}
    result = summarize({}, lock, {})
    assert result.rows[0]["intervals"]["R"] == [0., 1.]
    assert result.certificates["bright"]["0.05"] == "inconclusive"


def test_numerical_error_is_added_to_probability_enclosures():
    from seti_audit.inference import summarize

    lock = point_lock()
    lock["cells"][0]["deterministic"] = {"C": [1., 1.], "likelihood": [.9, .9], "R0": [.3, .3], "R": [.1, .1]}
    lock["cells"][0]["numerical_errors"] = {"R": .01}
    result = summarize({}, lock, {})
    assert result.rows[0]["intervals"]["R"] == pytest.approx([.09, .11])


def test_dark_obstruction_requires_every_original_demographic():
    from seti_audit.inference import summarize

    lock = point_lock()
    first = lock["cells"][0]
    first["deterministic"] = {"C": [1., 1.], "likelihood": [.9, .9], "R0": [.3, .3], "R": [.1, .1]}
    dark = deepcopy(first); dark.update(cell_id="dark", analytic_unit_weight=True); del dark["deterministic"]
    other = deepcopy(first); other.update(cell_id="other", baseline_id="uncovered")
    lock["cells"].extend([dark, other])
    result = summarize({}, lock, {})
    assert "analytic_obstruction" not in result.envelopes["bright"]["0.05"]
    assert result.certificates["bright"]["0.05"] == "inconclusive"
