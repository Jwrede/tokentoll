from __future__ import annotations

from tokentoll.config import ProjectConfig, resolve_for_path
from tokentoll.core.models import CallDiff, ChangeType, LLMCall
from tokentoll.pricing.engine import PricingEngine

_LINE_PROXIMITY = 10


def compute_diff(
    old_calls_map: dict[str, list[LLMCall]],
    new_calls_map: dict[str, list[LLMCall]],
    engine: PricingEngine,
    calls_per_month: int,
    config: ProjectConfig | None = None,
) -> list[CallDiff]:
    """Compare old and new LLM calls across all files."""
    all_files = set(old_calls_map.keys()) | set(new_calls_map.keys())
    diffs: list[CallDiff] = []

    for fpath in sorted(all_files):
        old_calls = old_calls_map.get(fpath, [])
        new_calls = new_calls_map.get(fpath, [])
        resolved = resolve_for_path(config, fpath) if config else None
        dm = resolved.default_model if resolved else None
        cpm = resolved.calls_per_month if resolved and resolved.calls_per_month else calls_per_month
        diffs.extend(_diff_file(old_calls, new_calls, engine, cpm, dm))

    return diffs


def _diff_file(
    old_calls: list[LLMCall],
    new_calls: list[LLMCall],
    engine: PricingEngine,
    calls_per_month: int,
    default_model: str | None = None,
) -> list[CallDiff]:
    matched_old: set[int] = set()
    matched_new: set[int] = set()
    diffs: list[CallDiff] = []

    for ni, nc in enumerate(new_calls):
        best_oi = _find_best_match(nc, old_calls, matched_old)
        if best_oi is not None:
            matched_old.add(best_oi)
            matched_new.add(ni)
            oc = old_calls[best_oi]

            old_est = engine.estimate(oc, calls_per_month, default_model=default_model)
            new_est = engine.estimate(nc, calls_per_month, default_model=default_model)

            if _calls_differ(oc, nc):
                delta = _compute_delta(old_est.monthly_estimate, new_est.monthly_estimate)
                cost_delta = _compute_delta(
                    old_est.estimated_cost_per_call, new_est.estimated_cost_per_call
                )
                diffs.append(
                    CallDiff(
                        change_type=ChangeType.MODIFIED,
                        old_call=oc,
                        new_call=nc,
                        old_estimate=old_est,
                        new_estimate=new_est,
                        cost_delta_per_call=cost_delta,
                        monthly_delta=delta,
                    )
                )

    for ni, nc in enumerate(new_calls):
        if ni not in matched_new:
            est = engine.estimate(nc, calls_per_month, default_model=default_model)
            diffs.append(
                CallDiff(
                    change_type=ChangeType.ADDED,
                    new_call=nc,
                    new_estimate=est,
                    monthly_delta=est.monthly_estimate,
                    cost_delta_per_call=est.estimated_cost_per_call,
                )
            )

    for oi, oc in enumerate(old_calls):
        if oi not in matched_old:
            est = engine.estimate(oc, calls_per_month, default_model=default_model)
            monthly = -est.monthly_estimate if est.monthly_estimate else None
            cost = -est.estimated_cost_per_call if est.estimated_cost_per_call else None
            diffs.append(
                CallDiff(
                    change_type=ChangeType.REMOVED,
                    old_call=oc,
                    old_estimate=est,
                    monthly_delta=monthly,
                    cost_delta_per_call=cost,
                )
            )

    return diffs


def _find_best_match(
    call: LLMCall,
    candidates: list[LLMCall],
    used: set[int],
) -> int | None:
    best_idx = None
    best_score = -1

    for i, c in enumerate(candidates):
        if i in used:
            continue
        if c.sdk != call.sdk or c.call_type != call.call_type:
            continue

        score = 0
        if c.raw_expression == call.raw_expression:
            score += 3
        line_dist = abs(c.line_number - call.line_number)
        if line_dist == 0:
            score += 5
        elif line_dist <= _LINE_PROXIMITY:
            score += 2
        else:
            continue
        if c.model == call.model:
            score += 2

        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx


def _calls_differ(a: LLMCall, b: LLMCall) -> bool:
    return a.model != b.model or a.max_tokens != b.max_tokens


def _compute_delta(old_val: float | None, new_val: float | None) -> float | None:
    if new_val is not None and old_val is not None:
        return new_val - old_val
    if new_val is not None:
        return new_val
    if old_val is not None:
        return -old_val
    return None
