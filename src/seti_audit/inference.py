"""Integer-audit intervals, checkpoint error allocation, and range certificates."""

from dataclasses import asdict
import math
from numbers import Integral

import numpy as np
from scipy.stats import beta

from .contracts import AuditCounts, Summary, WeightBounds


def _inputs(flags, weights, uniforms):
    flags, weights, uniforms = np.asarray(flags), np.asarray(weights), np.asarray(uniforms)
    if flags.ndim != 1 or flags.dtype != np.bool_ or weights.shape != flags.shape or uniforms.shape != flags.shape:
        raise ValueError("One boolean flag and weight/uniform per independent history required")
    if np.any(~np.isfinite(weights) | (weights < 0) | (weights > 1)):
        raise ValueError("Weights must be probabilities")
    if np.any(~np.isfinite(uniforms) | (uniforms <= 0) | (uniforms >= 1)):
        raise ValueError("Audit uniforms must be in the open unit interval")
    return flags, weights, uniforms


def accumulate(arrival_flags, weights, uniforms) -> AuditCounts:
    flags, w, u = _inputs(arrival_flags, weights, uniforms)
    z = u <= w
    return AuditCounts(len(flags), int(np.sum(flags)), int(np.sum(z)), int(np.sum(flags & z)),
                       math.fsum(w), math.fsum(w[flags]), {})


def accumulate_bounds(arrival_flags, low_weights, high_weights, uniforms) -> AuditCounts:
    flags, low, u = _inputs(arrival_flags, low_weights, uniforms)
    _, high, _ = _inputs(arrival_flags, high_weights, uniforms)
    if np.any(low > high):
        raise ValueError("Reversed weight bounds")
    components, sums = {}, {}
    for suffix, w in (("low", low), ("high", high)):
        z = u <= w
        for q, selected in (("null", np.ones(len(flags), dtype=bool)), ("J", flags), ("K", ~flags)):
            components[f"{q}_{suffix}"] = int(np.sum(z & selected))
            sums[f"{q}_{suffix}"] = math.fsum(w[selected])
    return AuditCounts(len(flags), int(np.sum(flags)), components["null_low"], components["J_low"],
                       sums["null_low"], sums["J_low"], components, sums)


def exact_interval(successes: int, trials: int, alpha: float) -> WeightBounds:
    if (any(not isinstance(x, Integral) or isinstance(x, bool) for x in (successes, trials))
            or not 0 <= successes <= trials or not math.isfinite(alpha) or not 0 < alpha < 1):
        raise ValueError("Exact binomial intervals need integer counts and 0<alpha<1")
    if trials == 0:
        return WeightBounds(0., 1.)
    low = 0. if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    high = 1. if successes == trials else float(beta.isf(alpha / 2, successes + 1, trials - successes))
    return WeightBounds(low, high)


def alpha_at_checkpoint(pool_error: float, registry_size: int, checkpoint_index: int) -> float:
    if (not math.isfinite(pool_error) or not 0 < pool_error < 1
            or any(not isinstance(x, Integral) or isinstance(x, bool) or x < 1
                   for x in (registry_size, checkpoint_index))):
        raise ValueError("Positive registry size/checkpoint and valid pool error required")
    return pool_error / registry_size / checkpoint_index / (checkpoint_index + 1)


def partition_risk(J_low: WeightBounds, J_high: WeightBounds,
                   K_low: WeightBounds, K_high: WeightBounds) -> WeightBounds:
    lower_den = J_low.low + K_high.high
    upper_den = J_high.high + K_low.low
    return WeightBounds(J_low.low / lower_den if lower_den else 0.,
                        J_high.high / upper_den if upper_den else 1.)


def compatibility(likelihood: WeightBounds, tau: float) -> str:
    if not 0 < tau < 1:
        raise ValueError("Compatibility threshold must be in (0,1)")
    return "retained" if likelihood.low >= tau else "excluded" if likelihood.high < tau else "unresolved"


def certify_narrowing(baseline_upper: WeightBounds, post_upper: WeightBounds,
                      has_certified_retained: bool) -> str:
    if not has_certified_retained:
        return "inconclusive"
    L0, U0, Lpost, Upost = baseline_upper.low, baseline_upper.high, post_upper.low, post_upper.high
    if L0 > 0 and L0 - Upost >= .01 and 1 - Upost / L0 >= .25:
        return "material"
    if U0 == 0 or U0 - Lpost < .01 or 1 - Lpost / U0 < .25:
        return "nonmaterial"
    return "inconclusive"


def _inflate(bound, error):
    if not math.isfinite(error) or error < 0:
        raise ValueError("Invalid numerical error")
    return WeightBounds(max(0., bound.low - error), min(1., bound.high + error))


def summarize(counts_by_cell: dict[str, AuditCounts], protocol_lock: dict,
              checkpoint_indices: dict[str, int]) -> Summary:
    """Summarize frozen cells with one evidence record per unique interval ID.

    Deterministic results carry explicit validated enclosures. Missing cells
    remain in all applicable outer envelopes. Proposal diagnostics are separate
    AuditCounts (histories=proposals, arrivals=accepted proposals), referenced by
    survival metadata; survivor-stopped attempt ratios are never used here.
    """
    registry = protocol_lock["bound_registry"]
    items, pools = registry["items"], registry["pools"]
    if sum(p["A"] for p in pools.values()) > .05:
        raise ValueError("Familywise Monte Carlo error exceeds .05")
    for name, pool in pools.items():
        if pool["M"] != sum(item["pool"] == name for item in items.values()):
            raise ValueError("Registry pool size mismatch")
    evidence = {}

    def interval(item_id, successes, trials):
        if item_id in evidence:
            previous = evidence[item_id]
            if (previous["successes"], previous["trials"]) != (successes, trials):
                raise ValueError("Conflicting counts for a shared interval")
            return WeightBounds(*previous["interval"])
        item = items[item_id]
        pool = pools[item["pool"]]
        index = checkpoint_indices[item_id]
        alpha = alpha_at_checkpoint(pool["A"], pool["M"], index)
        bound = exact_interval(successes, trials, alpha)
        evidence[item_id] = {"successes": successes, "trials": trials, "checkpoint": index,
                             "pool": item["pool"], "alpha": alpha, "interval": [bound.low, bound.high]}
        return bound

    rows = []
    for cell in protocol_lock["cells"]:
        row = {key: value for key, value in cell.items() if key not in {"deterministic", "interval_ids", "survival"}}
        row["protocol_hash"] = protocol_lock.get("protocol_hash")
        bounds = {q: WeightBounds(0., 1.) for q in ("C", "R0", "likelihood", "R")}
        points = {q: None for q in bounds}
        statuses = {q: "unavailable" for q in bounds}
        n = counts_by_cell.get(cell["cell_id"])
        deterministic = cell.get("deterministic")
        if deterministic is not None and deterministic.get("status", "validated") == "validated":
            for q in bounds:
                bounds[q] = WeightBounds(*deterministic[q])
                points[q] = deterministic.get("estimates", {}).get(q)
                if points[q] is None and bounds[q].low == bounds[q].high:
                    points[q] = bounds[q].low
                statuses[q] = "validated_deterministic"
            row["completion_status"] = "validated_deterministic"
        else:
            survival = cell.get("survival", {})
            if "constant" in survival:
                constant = survival["constant"]
                bounds["C"] = WeightBounds(constant, constant)
                points["C"], statuses["C"] = constant, "analytic"
                if "diagnostic_cell_id" in survival:
                    diagnostic = counts_by_cell.get(survival["diagnostic_cell_id"])
                    if diagnostic is None or diagnostic.histories == 0:
                        bounds["C"] = WeightBounds(0., constant)
                        points["C"], statuses["C"] = None, "diagnostic_pending"
                    else:
                        acceptance = interval(survival["interval_id"], diagnostic.arrivals, diagnostic.histories)
                        bounds["C"] = WeightBounds(constant * acceptance.low, constant * acceptance.high)
                        points["C"] = constant * diagnostic.arrivals / diagnostic.histories
                        statuses["C"] = "separate_proposal_diagnostic"
            row["completion_status"] = "pending"
            if n is not None and n.histories:
                ids = cell["interval_ids"]
                original = counts_by_cell.get(cell["baseline_counts_id"]) if "baseline_counts_id" in cell else n
                if original is not None and original.histories:
                    bounds["R0"] = interval(ids["R0"], original.arrivals, original.histories)
                    points["R0"], statuses["R0"] = original.arrivals / original.histories, "estimated"
                if cell.get("ideal_reference"):
                    bounds["R"] = interval(ids["R"], n.arrivals, n.histories)
                    points["R"], statuses["R"] = n.arrivals / n.histories, "ideal_silence_conditional"
                    silence = cell["ideal_silence_probability"]
                    c = bounds["C"]
                    bounds["likelihood"] = WeightBounds(min(1., silence / c.high) if c.high else 0.,
                                                        min(1., silence / c.low) if c.low else 1.)
                    points["likelihood"] = silence / points["C"] if points["C"] else None
                    statuses["likelihood"] = "analytic_silence_over_survival"
                elif cell.get("analytic_unconstrained_detector"):
                    statuses["likelihood"] = statuses["R"] = "unconstrained_detector_outer"
                elif n.bound_counts:
                    parts = {q: interval(ids[q], k, n.histories) for q, k in n.bound_counts.items()}
                    bounds["likelihood"] = WeightBounds(parts["null_low"].low, parts["null_high"].high)
                    bounds["R"] = partition_risk(parts["J_low"], parts["J_high"], parts["K_low"], parts["K_high"])
                    statuses["R"] = statuses["likelihood"] = "nuisance_bounds"
                    sums = n.bound_sums
                    point_r = partition_risk(*(WeightBounds(sums[q] / n.histories, sums[q] / n.histories)
                                               for q in ("J_low", "J_high", "K_low", "K_high")))
                    row["weighted_point_bounds"] = {"likelihood": [sums["null_low"] / n.histories, sums["null_high"] / n.histories],
                                                     "R": [point_r.low, point_r.high]}
                elif not cell.get("analytic_unit_weight"):
                    bounds["likelihood"] = interval(ids["likelihood"], n.nulls, n.histories)
                    bounds["R"] = interval(ids["R"], n.arrival_nulls, n.nulls)
                    points["likelihood"] = n.sum_w / n.histories
                    points["R"] = n.sum_bw / n.sum_w if n.sum_w else None
                    statuses["likelihood"] = "estimated"
                    statuses["R"] = "estimated" if n.sum_w else "undefined_zero_weight"
                row["completion_status"] = "estimated"
            if cell.get("analytic_unit_weight"):
                bounds["likelihood"] = WeightBounds(1., 1.)
                points["likelihood"], statuses["likelihood"] = 1., "analytic"
                bounds["R"], points["R"], statuses["R"] = bounds["R0"], points["R0"], "identity_R0"
        errors = cell.get("numerical_errors", {})
        bounds = {q: _inflate(bound, errors.get(q, 0.)) for q, bound in bounds.items()}
        row.update(estimates=points, estimate_status=statuses, numerical_errors=errors,
                   intervals={q: [b.low, b.high] for q, b in bounds.items()},
                   counts=asdict(n) if n is not None else None,
                   compatibility={str(t): compatibility(bounds["likelihood"], t) for t in protocol_lock["thresholds"]})
        rows.append(row)

    certified, possible, envelopes, certificates = {}, {}, {}, {}
    families = sorted({family for row in rows for family in row.get("families", ())})
    for family in families:
        members = [r for r in rows if family in r.get("families", ())]
        certified[family], possible[family], envelopes[family], certificates[family] = {}, {}, {}, {}

        def enclosure(selected, quantity):
            return [min(r["intervals"][quantity][0] for r in selected), max(r["intervals"][quantity][1] for r in selected)] if selected else None

        baseline = WeightBounds(max(r["intervals"]["R0"][0] for r in members), max(r["intervals"]["R0"][1] for r in members))
        # A unit-weight counterpart for every original baseline proves that
        # family's entire original risk range is still present, independent of
        # statistical uncertainty in the risk values themselves.
        baseline_ids = {r.get("baseline_id") for r in members}
        dark_ids = {r.get("baseline_id") for r in members if r.get("analytic_unit_weight")}
        obstruction = None not in baseline_ids and baseline_ids <= dark_ids
        for tau in protocol_lock["thresholds"]:
            key = str(tau)
            retained = [r for r in members if r["compatibility"][key] == "retained"]
            maybe = [r for r in members if r["compatibility"][key] != "excluded"]
            certified[family][key] = [r["cell_id"] for r in retained]
            possible[family][key] = [r["cell_id"] for r in maybe]
            entry = {"I0": enclosure(members, "R0"), "Iselect": enclosure(maybe, "R0"),
                     "Ipost": enclosure(maybe, "R"), "certified_post": enclosure(retained, "R"),
                     "baseline_upper": [baseline.low, baseline.high]}
            if not maybe:
                certificate = "incompatible"
                entry["post_upper"] = None
            else:
                post = WeightBounds(max((r["intervals"]["R"][0] for r in retained), default=0.),
                                    max(r["intervals"]["R"][1] for r in maybe))
                entry["post_upper"] = [post.low, post.high]
                entry["absolute_contraction_bounds"] = [baseline.low - post.high, baseline.high - post.low]
                entry["relative_contraction_bounds"] = [1 - post.high / baseline.low if baseline.low else None,
                                                         1 - post.low / baseline.high if baseline.high else 0.]
                certificate = certify_narrowing(baseline, post, bool(retained))
                if obstruction:
                    certificate = "nonmaterial"
                    entry["analytic_obstruction"] = "unit_weight_counterparts"
            envelopes[family][key], certificates[family][key] = entry, certificate
    return Summary(tuple(rows), certified, possible, envelopes, certificates, evidence)
