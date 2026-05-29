"""Verdict rendering in the markdown formatter.

Regression coverage for v0.8.2: the PASS verdict was previously silent
even when a policy was configured, which made the CI gate invisible on
clean PRs. The formatter now renders a PASS banner whenever a Verdict
is passed in, and pipeline.py decides whether to pass a Verdict by
checking whether the project's policy is non-empty.
"""

from __future__ import annotations

from tokentoll.core.models import (
    CallDiff,
    CallType,
    ChangeType,
    CostEstimate,
    DiffReport,
    LLMCall,
    ModelPricing,
    Verdict,
    VerdictFinding,
    VerdictLevel,
)
from tokentoll.output.markdown import format_diff_report_markdown


def _diff() -> DiffReport:
    call = LLMCall(
        file_path="src/agent.py",
        line_number=10,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model="gpt-4o",
        model_is_literal=True,
        max_tokens=1000,
        raw_expression="client.chat.completions.create",
    )
    est = CostEstimate(
        call=call,
        pricing=ModelPricing(
            model_name="gpt-4o",
            input_cost_per_token=2.5e-6,
            output_cost_per_token=1e-5,
        ),
        estimated_cost_per_call=0.01,
        monthly_estimate=10.0,
        model_found=True,
    )
    diff = CallDiff(
        change_type=ChangeType.ADDED,
        new_call=call,
        new_estimate=est,
        monthly_delta=10.0,
        cost_delta_per_call=0.01,
    )
    return DiffReport(
        base_ref="main",
        head_ref="HEAD",
        call_diffs=[diff],
        total_monthly_delta=10.0,
        total_calls_added=1,
        assumptions=["10000 calls/month per call site"],
    )


def test_verdict_none_omits_banner():
    out = format_diff_report_markdown(_diff(), verdict=None)
    assert "tokentoll verdict" not in out


def test_pass_verdict_renders_banner_with_subtitle():
    verdict = Verdict(level=VerdictLevel.PASS, findings=[])
    out = format_diff_report_markdown(_diff(), verdict=verdict)
    assert "## tokentoll verdict: PASS" in out
    assert "All configured budgets and rules were satisfied." in out
    # PASS gets no "Required action" hint
    assert "Required action" not in out


def test_fail_verdict_renders_blocking_findings():
    verdict = Verdict(
        level=VerdictLevel.FAIL,
        findings=[
            VerdictFinding(
                severity=VerdictLevel.FAIL,
                rule="max_relative_increase",
                message="per-call cost grew 16.7x (threshold 5x)",
                file_path="src/agent.py",
                line_number=10,
            )
        ],
    )
    out = format_diff_report_markdown(_diff(), verdict=verdict)
    assert "## tokentoll verdict: FAIL" in out
    assert "**Blocking findings (1):**" in out
    assert "per-call cost grew 16.7x" in out
    assert "Required action:" in out
    assert "All configured budgets" not in out


def test_pass_with_findings_renders_findings_not_subtitle():
    """If a PASS verdict somehow carries findings (future WARN tier),
    show the findings rather than the satisfied-subtitle."""
    verdict = Verdict(
        level=VerdictLevel.PASS,
        findings=[
            VerdictFinding(
                severity=VerdictLevel.WARN,
                rule="hypothetical_warn",
                message="just a heads-up",
            )
        ],
    )
    out = format_diff_report_markdown(_diff(), verdict=verdict)
    assert "## tokentoll verdict: PASS" in out
    assert "All configured budgets" not in out
