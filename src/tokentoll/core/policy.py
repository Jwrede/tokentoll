from __future__ import annotations

from tokentoll.config import Policy
from tokentoll.core.models import (
    CallDiff,
    ChangeType,
    DiffReport,
    Verdict,
    VerdictFinding,
    VerdictLevel,
)


def evaluate_policy(report: DiffReport, policy: Policy) -> Verdict:
    """Evaluate a diff report against a policy and return a Verdict.

    The returned Verdict.level is FAIL if any rule fired, WARN if only
    warn-tier rules fired, PASS otherwise. v0.7 only emits FAIL findings;
    WARN/PASS slots are reserved for follow-up.
    """
    findings: list[VerdictFinding] = []

    if policy.is_empty():
        return Verdict(level=VerdictLevel.PASS, findings=findings)

    findings.extend(_check_per_callsite_rules(report.call_diffs, policy))
    findings.extend(_check_aggregate_rules(report, policy))

    level = _max_severity(findings)
    return Verdict(level=level, findings=findings)


def _check_per_callsite_rules(diffs: list[CallDiff], policy: Policy) -> list[VerdictFinding]:
    findings: list[VerdictFinding] = []
    for d in diffs:
        if d.change_type == ChangeType.UNCHANGED:
            continue
        findings.extend(_check_unknown_model(d, policy))
        findings.extend(_check_relative_increase(d, policy))
        findings.extend(_check_callsite_budget(d, policy))
    return findings


def _check_unknown_model(d: CallDiff, policy: Policy) -> list[VerdictFinding]:
    if not policy.rules.block_unknown_models:
        return []
    if d.change_type not in (ChangeType.ADDED, ChangeType.MODIFIED):
        return []
    est = d.new_estimate
    call = d.new_call
    if est is None or call is None:
        return []
    if est.model_found:
        return []
    model_label = call.model or est.used_default_model or "<dynamic>"
    return [
        VerdictFinding(
            severity=VerdictLevel.FAIL,
            rule="block_unknown_models",
            message=f"unknown or unpriced model `{model_label}`",
            file_path=call.file_path,
            line_number=call.line_number,
        )
    ]


def _check_relative_increase(d: CallDiff, policy: Policy) -> list[VerdictFinding]:
    threshold = policy.budgets.max_relative_increase
    if threshold is None:
        return []
    if d.change_type != ChangeType.MODIFIED:
        return []
    if d.old_estimate is None or d.new_estimate is None:
        return []
    old = d.old_estimate.estimated_cost_per_call
    new = d.new_estimate.estimated_cost_per_call
    if old is None or new is None or old <= 0:
        return []
    ratio = new / old
    if ratio <= threshold:
        return []
    call = d.new_call or d.old_call
    file_path = call.file_path if call else None
    line_number = call.line_number if call else None
    return [
        VerdictFinding(
            severity=VerdictLevel.FAIL,
            rule="max_relative_increase",
            message=f"per-call cost grew {ratio:.1f}x (threshold {threshold:g}x)",
            file_path=file_path,
            line_number=line_number,
        )
    ]


def _check_callsite_budget(d: CallDiff, policy: Policy) -> list[VerdictFinding]:
    threshold = policy.budgets.max_callsite_monthly_usd
    if threshold is None:
        return []
    if d.change_type not in (ChangeType.ADDED, ChangeType.MODIFIED):
        return []
    delta = d.monthly_delta
    if delta is None or delta <= threshold:
        return []
    call = d.new_call or d.old_call
    file_path = call.file_path if call else None
    line_number = call.line_number if call else None
    return [
        VerdictFinding(
            severity=VerdictLevel.FAIL,
            rule="max_callsite_monthly_usd",
            message=f"call site adds ${delta:.2f}/mo (threshold ${threshold:.2f}/mo)",
            file_path=file_path,
            line_number=line_number,
        )
    ]


def _check_aggregate_rules(report: DiffReport, policy: Policy) -> list[VerdictFinding]:
    findings: list[VerdictFinding] = []
    threshold = policy.budgets.max_monthly_delta_usd
    total = report.total_monthly_delta
    if threshold is not None and total is not None and total > threshold:
        findings.append(
            VerdictFinding(
                severity=VerdictLevel.FAIL,
                rule="max_monthly_delta_usd",
                message=(f"total monthly delta +${total:.2f} exceeds budget ${threshold:.2f}"),
            )
        )
    return findings


def _max_severity(findings: list[VerdictFinding]) -> VerdictLevel:
    if any(f.severity == VerdictLevel.FAIL for f in findings):
        return VerdictLevel.FAIL
    if any(f.severity == VerdictLevel.WARN for f in findings):
        return VerdictLevel.WARN
    return VerdictLevel.PASS
