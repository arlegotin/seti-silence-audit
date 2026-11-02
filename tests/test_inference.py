from itertools import product
import math

import numpy as np
import pytest


def point_lock(cell_id="c"):
    quantities = ("R0", "likelihood", "R")
    return {"protocol_hash": "synthetic-control", "thresholds": [.01, .05, .1],
            "cells": [{"cell_id": cell_id, "families": ["bright"], "baseline_id": "base",
                       "interval_ids": {q: q for q in quantities}, "survival": {"constant": 1.}}],
            "bound_registry": {"items": {q: {"pool": "primary"} for q in quantities},
                               "pools": {"primary": {"A": .025, "M": 3}}}}


def test_signed_updating_controls_use_weighted_points_and_integer_audit_counts():
    from seti_audit.inference import accumulate, summarize

    flags = np.array([True, False])
    for weights, expected in (([1., .06], .5 / .53), ([.06, 1.], .03 / .53)):
        counts = accumulate(flags, np.array(weights), np.array([.5, .5]))
        result = summarize({"c": counts}, point_lock(), {q: 1 for q in ("R0", "likelihood", "R")})
        row = result.rows[0]
        assert row["estimates"]["R0"] == .5
        assert row["estimates"]["likelihood"] == .53
        assert row["estimates"]["R"] == pytest.approx(expected)
        assert isinstance(counts.nulls, int)


def test_zero_null_draws_remain_unidentified_and_zero_weight_has_no_point():
    from seti_audit.inference import accumulate, summarize

    counts = accumulate(np.array([True, False]), np.array([.1, .1]), np.array([.8, .9]))
    row = summarize({"c": counts}, point_lock(), {q: 1 for q in ("R0", "likelihood", "R")}).rows[0]
    assert row["intervals"]["R"] == [0., 1.]
    assert row["estimates"]["R"] == .5
    zero = accumulate(np.array([True, False]), np.array([0., 0.]), np.array([.8, .9]))
    row = summarize({"c": zero}, point_lock(), {q: 1 for q in ("R0", "likelihood", "R")}).rows[0]
    assert row["estimates"]["R"] is None
    assert row["estimate_status"]["R"] == "undefined_zero_weight"
    assert row["intervals"]["R"] == [0., 1.]


def test_exact_intervals_reject_weighted_successes_and_preserve_zero_event_uncertainty():
    from seti_audit.inference import exact_interval

    assert exact_interval(0, 0, .05).low == 0
    assert exact_interval(0, 0, .05).high == 1
    assert exact_interval(0, 10, .05).high == pytest.approx(.3084971078187608)
    assert exact_interval(10, 10, .05).low == pytest.approx(.6915028921812392)
    for successes, trials in ((.5, 10), (1, 1.5), (11, 10), (-1, 10), (True, 10)):
        with pytest.raises(ValueError):
            exact_interval(successes, trials, .05)


@pytest.mark.parametrize("uniforms", [[0., .5], [.5, 1.], [math.nan, .5]])
def test_audit_uniforms_are_open_and_finite(uniforms):
    from seti_audit.inference import accumulate

    with pytest.raises(ValueError, match="uniform"):
        accumulate(np.array([True, False]), np.array([.5, .5]), np.array(uniforms))


def test_interval_partition_bounds_contain_every_small_nuisance_case():
    from seti_audit.inference import partition_risk, accumulate_bounds
    from seti_audit.contracts import WeightBounds

    low = np.array([.1, .3, .2, .4]); high = np.array([.6, .9, .8, 1.])
    flags = np.array([True, True, False, False])
    Jlo, Jhi, Klo, Khi = .1, .375, .15, .45
    interval = partition_risk(WeightBounds(Jlo, Jlo), WeightBounds(Jhi, Jhi),
                              WeightBounds(Klo, Klo), WeightBounds(Khi, Khi))
    assert interval.low == pytest.approx(Jlo / (Jlo + Khi))
    assert interval.high == pytest.approx(Jhi / (Jhi + Klo))
    for choices in product((0, 1), repeat=4):
        w = np.where(choices, high, low)
        risk = np.sum(w[flags]) / np.sum(w)
        assert interval.low <= risk <= interval.high
    counts = accumulate_bounds(flags, low, high, np.array([.05, .5, .7, .95]))
    assert counts.bound_counts == {"null_low": 1, "null_high": 4, "J_low": 1, "J_high": 2, "K_low": 0, "K_high": 2}
    assert counts.bound_sums["J_high"] == pytest.approx(1.5)


def test_checkpoint_error_is_summable_without_reallocating_for_thresholds():
    from seti_audit.inference import alpha_at_checkpoint, accumulate, summarize

    assert alpha_at_checkpoint(.025, 17, 1) == .025 / 34
    allocation = 17 * sum(alpha_at_checkpoint(.025, 17, j) for j in range(1, 10001))
    assert allocation < .025
    assert allocation == pytest.approx(.025 * 10000 / 10001)
    counts = accumulate(np.array([True, False]), np.ones(2), np.array([.2, .8]))
    result = summarize({"c": counts}, point_lock(), {q: 2 for q in ("R0", "likelihood", "R")})
    assert len(result.interval_evidence) == 3
    assert all(e["alpha"] == .025 / (3 * 2 * 3) for e in result.interval_evidence.values())
    for values in ((.025, 0, 1), (.025, 3, 0), (.025, 3, 1.5)):
        with pytest.raises(ValueError):
            alpha_at_checkpoint(*values)


def test_bounds_summary_uses_registry_and_separate_survival_diagnostic():
    from seti_audit.contracts import AuditCounts
    from seti_audit.inference import accumulate_bounds, exact_interval, summarize

    counts = accumulate_bounds(np.array([True, False] * 1000), np.full(2000, .4),
                               np.full(2000, .8), np.linspace(.0001, .9999, 2000))
    quantities = ("R0", "null_low", "null_high", "J_low", "J_high", "K_low", "K_high", "acceptance")
    lock = point_lock()
    lock["cells"][0]["interval_ids"] = {q: q for q in quantities if q != "acceptance"}
    lock["cells"][0]["survival"] = {"constant": .2, "diagnostic_cell_id": "proposal",
                                    "interval_id": "acceptance"}
    lock["bound_registry"] = {"items": {q: {"pool": "diagnostics"} for q in quantities},
                              "pools": {"diagnostics": {"A": .025, "M": len(quantities)}}}
    proposal = AuditCounts(100, 80, 0, 0, 0., 0., {})
    result = summarize({"c": counts, "proposal": proposal}, lock, {q: 1 for q in quantities})
    row = result.rows[0]
    acceptance = exact_interval(80, 100, .025 / (8 * 2))
    assert row["intervals"]["C"] == [.2 * acceptance.low, .2 * acceptance.high]
    assert row["estimates"]["C"] == pytest.approx(.16)
    assert row["estimates"]["R"] is None
    assert row["estimate_status"]["R"] == "nuisance_bounds"
    assert row["intervals"]["R"][0] < .5 < row["intervals"]["R"][1]
    assert len(result.interval_evidence) == 8


def test_aggregate_rejects_components_exceeding_arrival_partition():
    from seti_audit.contracts import AuditCounts

    # Every count is <=n and each side sums to its null count; J_high still
    # cannot exceed the ONE arrival in these four histories.
    components = {"null_low": 1, "null_high": 4, "J_low": 1, "J_high": 3, "K_low": 0, "K_high": 1}
    with pytest.raises(ValueError, match="partition"):
        AuditCounts(4, 1, 1, 1, 1., 1., components, {q: float(v) for q, v in components.items()})
