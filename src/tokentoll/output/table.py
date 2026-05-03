from __future__ import annotations

import sys

from tokentoll.core.models import CostEstimate, DiffReport, ScanReport


def _model_display(model: str | None, est: CostEstimate | None = None) -> str:
    if model:
        return model
    if est and est.used_default_model:
        return f"{est.used_default_model} (default)"
    return "<dynamic>"


def _fmt_cost(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val < 0.01:
        return f"${val:.6f}"
    return f"${val:.2f}"


def _fmt_delta(val: float | None) -> str:
    if val is None:
        return "N/A"
    sign = "+" if val > 0 else ""
    if abs(val) < 0.01:
        return f"{sign}${val:.6f}"
    return f"{sign}${val:.2f}"


def print_scan_report(report: ScanReport) -> None:
    if not report.estimates:
        print("No LLM API calls detected.")
        return

    print("LLM API Calls Detected")
    print("=" * 60)
    print()

    current_file = None
    for est in report.estimates:
        if est.call.file_path != current_file:
            current_file = est.call.file_path
            print(f"File: {current_file}")

        model_str = _model_display(est.call.model, est)
        max_tok_str = str(est.call.max_tokens) if est.call.max_tokens else "default"

        print(f"  Line {est.call.line_number}: {est.call.sdk} {est.call.raw_expression}")
        print(f"           Model: {model_str} | Max tokens: {max_tok_str}")

        if est.model_found:
            print(
                f"           Est. cost/call: {_fmt_cost(est.estimated_cost_per_call)} "
                f"| Monthly ({report.assumptions[0] if report.assumptions else '?'}): "
                f"{_fmt_cost(est.monthly_estimate)}"
            )
        else:
            for note in est.notes:
                print(f"           {note}")
        print()

    print("--")
    print(f"Total estimated monthly cost: {_fmt_cost(report.total_monthly_estimate)}")

    for assumption in report.assumptions:
        print(f"  {assumption}")

    for warning in report.warnings:
        print(f"  Warning: {warning}", file=sys.stderr)


def print_diff_report(report: DiffReport) -> None:
    if not report.call_diffs:
        print("No LLM API call changes detected.")
        return

    print(f"LLM Cost Diff: {report.base_ref}..{report.head_ref}")
    print("=" * 60)
    print()

    for d in report.call_diffs:
        if d.change_type.value == "unchanged":
            continue

        call = d.new_call or d.old_call
        if call is None:
            continue

        prefix = {"added": "+", "removed": "-", "modified": "~"}[d.change_type.value]
        label = d.change_type.value.upper()

        print(f"{prefix} {label:8s} {call.file_path}:{call.line_number}")

        if d.change_type.value == "modified" and d.old_call and d.new_call:
            old_model = _model_display(d.old_call.model, d.old_estimate)
            new_model = _model_display(d.new_call.model, d.new_estimate)
            print(f"          {call.sdk} | Model: {old_model} -> {new_model}")
            if d.old_estimate and d.new_estimate:
                print(
                    f"          Est. cost/call: "
                    f"{_fmt_cost(d.old_estimate.estimated_cost_per_call)} -> "
                    f"{_fmt_cost(d.new_estimate.estimated_cost_per_call)} "
                    f"| Monthly: {_fmt_delta(d.monthly_delta)}"
                )
        elif d.change_type.value == "added":
            est = d.new_estimate
            model_str = _model_display(call.model, est)
            print(f"          {call.sdk} | Model: {model_str}")
            if est and est.model_found:
                print(
                    f"          Est. cost/call: {_fmt_cost(est.estimated_cost_per_call)} "
                    f"| Monthly: {_fmt_delta(d.monthly_delta)}"
                )
        elif d.change_type.value == "removed":
            est = d.old_estimate
            model_str = _model_display(call.model, est)
            print(f"          {call.sdk} | Model: {model_str}")
            if est and est.model_found:
                print(f"          Monthly: {_fmt_delta(d.monthly_delta)}")

        print()

    print("--")
    print(f"Monthly cost impact: {_fmt_delta(report.total_monthly_delta)}")
    print(
        f"  Added: {report.total_calls_added} | "
        f"Changed: {report.total_calls_modified} | "
        f"Removed: {report.total_calls_removed}"
    )

    for assumption in report.assumptions:
        print(f"  {assumption}")

    for warning in report.warnings:
        print(f"  Warning: {warning}", file=sys.stderr)
