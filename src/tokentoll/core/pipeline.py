from __future__ import annotations

import json

from tokentoll.core.models import (
    ChangeType,
    CostEstimate,
    DiffReport,
    ScanReport,
)
from tokentoll.pricing.engine import PricingEngine
from tokentoll.scanner.python_scanner import scan_paths, scan_source


def _build_scan_report(
    estimates: list[CostEstimate],
    calls_per_month: int,
    engine_warnings: list[str],
) -> ScanReport:
    total = 0.0
    for est in estimates:
        if est.monthly_estimate is not None:
            total += est.monthly_estimate

    return ScanReport(
        estimates=estimates,
        total_monthly_estimate=total if estimates else None,
        warnings=engine_warnings,
        assumptions=[f"{calls_per_month} calls/month per call site"],
    )


def run_scan(paths: list[str], output_format: str, calls_per_month: int) -> int:
    calls = scan_paths(paths)
    engine = PricingEngine()

    estimates = [engine.estimate(call, calls_per_month) for call in calls]
    report = _build_scan_report(estimates, calls_per_month, engine.warnings)

    if output_format == "json":
        from tokentoll.output.json_output import format_scan_report_json

        print(json.dumps(format_scan_report_json(report), indent=2))
    elif output_format == "markdown":
        from tokentoll.output.markdown import format_scan_report_markdown

        print(format_scan_report_markdown(report))
    else:
        from tokentoll.output.table import print_scan_report

        print_scan_report(report)

    return 0


def run_diff_command(
    ref: str | None,
    base: str | None,
    head: str | None,
    output_format: str,
    calls_per_month: int,
) -> int:
    from tokentoll.diff.git import get_changed_files, get_file_at_ref

    if base and head:
        base_ref, head_ref = base, head
    elif ref and ".." in ref:
        base_ref, head_ref = ref.split("..", 1)
    elif ref:
        base_ref, head_ref = ref, "HEAD"
    else:
        base_ref, head_ref = "HEAD~1", "HEAD"

    changed_files = get_changed_files(base_ref, head_ref)
    if not changed_files:
        print("No Python files changed.")
        return 0

    engine = PricingEngine()

    old_calls_map: dict[str, list] = {}
    new_calls_map: dict[str, list] = {}

    for fpath, status in changed_files:
        if status != "D":
            source = get_file_at_ref(head_ref, fpath)
            if source:
                new_calls_map[fpath] = scan_source(source, fpath)

        if status != "A":
            source = get_file_at_ref(base_ref, fpath)
            if source:
                old_calls_map[fpath] = scan_source(source, fpath)

    from tokentoll.diff.engine import compute_diff

    call_diffs = compute_diff(old_calls_map, new_calls_map, engine, calls_per_month)

    total_delta = 0.0
    added = removed = modified = 0
    for d in call_diffs:
        if d.monthly_delta is not None:
            total_delta += d.monthly_delta
        if d.change_type == ChangeType.ADDED:
            added += 1
        elif d.change_type == ChangeType.REMOVED:
            removed += 1
        elif d.change_type == ChangeType.MODIFIED:
            modified += 1

    report = DiffReport(
        base_ref=base_ref,
        head_ref=head_ref,
        call_diffs=call_diffs,
        total_monthly_delta=total_delta,
        total_calls_added=added,
        total_calls_removed=removed,
        total_calls_modified=modified,
        warnings=engine.warnings,
        assumptions=[f"{calls_per_month} calls/month per call site"],
    )

    if output_format == "json":
        from tokentoll.output.json_output import format_diff_report_json

        print(json.dumps(format_diff_report_json(report), indent=2))
    elif output_format in ("markdown", "github-comment"):
        from tokentoll.output.markdown import format_diff_report_markdown

        print(format_diff_report_markdown(report))
    else:
        from tokentoll.output.table import print_diff_report

        print_diff_report(report)

    return 0
