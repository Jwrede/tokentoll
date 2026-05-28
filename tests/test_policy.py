from __future__ import annotations

from tokentoll.config import Policy, PolicyBudgets, PolicyRules
from tokentoll.core.models import (
    CallDiff,
    CallType,
    ChangeType,
    CostEstimate,
    DiffReport,
    LLMCall,
    ModelPricing,
    VerdictLevel,
)
from tokentoll.core.policy import evaluate_policy


def _call(model: str = "gpt-4o", line: int = 10, fpath: str = "src/agent.py") -> LLMCall:
    return LLMCall(
        file_path=fpath,
        line_number=line,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model=model,
        model_is_literal=True,
        max_tokens=1000,
        raw_expression="client.chat.completions.create",
    )


def _estimate(
    call: LLMCall,
    cost_per_call: float | None = 0.01,
    monthly: float | None = 10.0,
    model_found: bool = True,
) -> CostEstimate:
    pricing = (
        ModelPricing(
            model_name=call.model or "unknown",
            input_cost_per_token=1e-6,
            output_cost_per_token=2e-6,
        )
        if model_found
        else None
    )
    return CostEstimate(
        call=call,
        pricing=pricing,
        estimated_cost_per_call=cost_per_call,
        monthly_estimate=monthly,
        model_found=model_found,
    )


def _report(diffs: list[CallDiff], total: float | None = None) -> DiffReport:
    return DiffReport(
        base_ref="main",
        head_ref="HEAD",
        call_diffs=diffs,
        total_monthly_delta=total,
        total_calls_added=sum(1 for d in diffs if d.change_type == ChangeType.ADDED),
        total_calls_removed=sum(1 for d in diffs if d.change_type == ChangeType.REMOVED),
        total_calls_modified=sum(1 for d in diffs if d.change_type == ChangeType.MODIFIED),
    )


def test_empty_policy_returns_pass_with_no_findings():
    call = _call()
    diff = CallDiff(
        change_type=ChangeType.MODIFIED,
        old_call=call,
        new_call=call,
        old_estimate=_estimate(call, cost_per_call=0.01, monthly=10.0),
        new_estimate=_estimate(call, cost_per_call=10.0, monthly=10000.0),
        monthly_delta=9990.0,
    )
    report = _report([diff], total=9990.0)

    verdict = evaluate_policy(report, Policy())

    assert verdict.level == VerdictLevel.PASS
    assert verdict.findings == []


def test_max_monthly_delta_fail():
    call = _call()
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=call,
        new_estimate=_estimate(call, monthly=500.0),
        monthly_delta=500.0,
    )
    report = _report([diff], total=500.0)
    policy = Policy(budgets=PolicyBudgets(max_monthly_delta_usd=250.0))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.FAIL
    assert any(f.rule == "max_monthly_delta_usd" for f in verdict.findings)


def test_max_monthly_delta_pass_under_threshold():
    call = _call()
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=call,
        new_estimate=_estimate(call, monthly=100.0),
        monthly_delta=100.0,
    )
    report = _report([diff], total=100.0)
    policy = Policy(budgets=PolicyBudgets(max_monthly_delta_usd=250.0))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.PASS


def test_max_relative_increase_fail_on_model_swap():
    old_call = _call(model="gpt-4o-mini")
    new_call = _call(model="gpt-4o")
    diff = CallDiff(
        change_type=ChangeType.MODIFIED,
        old_call=old_call,
        new_call=new_call,
        old_estimate=_estimate(old_call, cost_per_call=0.001, monthly=1.0),
        new_estimate=_estimate(new_call, cost_per_call=0.015, monthly=15.0),
        monthly_delta=14.0,
    )
    report = _report([diff], total=14.0)
    policy = Policy(budgets=PolicyBudgets(max_relative_increase=5.0))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.FAIL
    rels = [f for f in verdict.findings if f.rule == "max_relative_increase"]
    assert len(rels) == 1
    assert rels[0].file_path == "src/agent.py"
    assert rels[0].line_number == 10
    assert "15.0x" in rels[0].message


def test_max_relative_increase_pass_under_threshold():
    old_call = _call(model="gpt-4o-mini")
    new_call = _call(model="gpt-4o-mini")
    diff = CallDiff(
        change_type=ChangeType.MODIFIED,
        old_call=old_call,
        new_call=new_call,
        old_estimate=_estimate(old_call, cost_per_call=0.001, monthly=1.0),
        new_estimate=_estimate(new_call, cost_per_call=0.002, monthly=2.0),
        monthly_delta=1.0,
    )
    report = _report([diff], total=1.0)
    policy = Policy(budgets=PolicyBudgets(max_relative_increase=5.0))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.PASS


def test_max_relative_increase_skips_non_modified():
    new_call = _call(model="gpt-4o")
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=new_call,
        new_estimate=_estimate(new_call, cost_per_call=0.05, monthly=50.0),
        monthly_delta=50.0,
    )
    report = _report([diff], total=50.0)
    policy = Policy(budgets=PolicyBudgets(max_relative_increase=5.0))

    verdict = evaluate_policy(report, policy)

    assert not any(f.rule == "max_relative_increase" for f in verdict.findings)


def test_max_callsite_monthly_fail():
    new_call = _call(model="claude-opus")
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=new_call,
        new_estimate=_estimate(new_call, monthly=480.0),
        monthly_delta=480.0,
    )
    report = _report([diff], total=480.0)
    policy = Policy(budgets=PolicyBudgets(max_callsite_monthly_usd=100.0))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.FAIL
    findings = [f for f in verdict.findings if f.rule == "max_callsite_monthly_usd"]
    assert len(findings) == 1
    assert "480.00" in findings[0].message


def test_block_unknown_models_fail_on_added_unknown():
    new_call = _call(model="some-private-model")
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=new_call,
        new_estimate=_estimate(new_call, cost_per_call=None, monthly=None, model_found=False),
        monthly_delta=None,
    )
    report = _report([diff])
    policy = Policy(rules=PolicyRules(block_unknown_models=True))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.FAIL
    findings = [f for f in verdict.findings if f.rule == "block_unknown_models"]
    assert len(findings) == 1
    assert "some-private-model" in findings[0].message


def test_block_unknown_models_off_by_default():
    new_call = _call(model="some-private-model")
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=new_call,
        new_estimate=_estimate(new_call, model_found=False),
        monthly_delta=None,
    )
    report = _report([diff])
    policy = Policy(budgets=PolicyBudgets(max_monthly_delta_usd=1.0))

    verdict = evaluate_policy(report, policy)

    assert not any(f.rule == "block_unknown_models" for f in verdict.findings)


def test_block_unknown_models_ignores_removed():
    old_call = _call(model="some-private-model")
    diff = CallDiff(
        change_type=ChangeType.REMOVED,
        old_call=old_call,
        old_estimate=_estimate(old_call, model_found=False),
        monthly_delta=None,
    )
    report = _report([diff])
    policy = Policy(rules=PolicyRules(block_unknown_models=True))

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.PASS


def test_multiple_findings_aggregate_to_fail():
    call = _call(model="gpt-4o")
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=call,
        new_estimate=_estimate(call, monthly=500.0),
        monthly_delta=500.0,
    )
    report = _report([diff], total=500.0)
    policy = Policy(
        budgets=PolicyBudgets(
            max_monthly_delta_usd=250.0,
            max_callsite_monthly_usd=100.0,
        ),
    )

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.FAIL
    assert len(verdict.findings) >= 2


def test_unchanged_diffs_ignored():
    call = _call(model="gpt-4o")
    diff = CallDiff(
        change_type=ChangeType.UNCHANGED,
        old_call=call,
        new_call=call,
        old_estimate=_estimate(call, monthly=10000.0),
        new_estimate=_estimate(call, monthly=10000.0),
        monthly_delta=0.0,
    )
    report = _report([diff], total=0.0)
    policy = Policy(
        budgets=PolicyBudgets(max_callsite_monthly_usd=10.0),
        rules=PolicyRules(block_unknown_models=True),
    )

    verdict = evaluate_policy(report, policy)

    assert verdict.level == VerdictLevel.PASS
