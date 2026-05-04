from __future__ import annotations

import json
from pathlib import Path

from tokentoll.config import ProjectConfig, load_config, resolve_for_path
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


def run_scan(
    paths: list[str],
    output_format: str,
    calls_per_month: int | None,
    config_path: str | None = None,
) -> int:
    config = _load_project_config(config_path, paths)
    effective_cpm = calls_per_month or config.calls_per_month or 1000

    calls = scan_paths(paths)
    engine = PricingEngine()

    estimates = []
    for call in calls:
        resolved = resolve_for_path(config, call.file_path)
        cpm = calls_per_month or resolved.calls_per_month or effective_cpm
        estimates.append(
            engine.estimate(
                call,
                cpm,
                default_model=resolved.default_model,
                default_models=resolved.default_models,
                skip_dynamic_models=resolved.skip_dynamic_models,
            )
        )

    report = _build_scan_report(estimates, effective_cpm, engine.warnings)

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


def _load_project_config(config_path: str | None, paths: list[str] | None = None) -> ProjectConfig:
    if config_path:
        from tokentoll.config import _parse_config_file

        return _parse_config_file(Path(config_path))
    search_from = Path(paths[0]).resolve() if paths else None
    return load_config(search_from)


def run_diff_command(
    ref: str | None,
    base: str | None,
    head: str | None,
    output_format: str,
    calls_per_month: int | None,
    config_path: str | None = None,
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

    config = _load_project_config(config_path)
    effective_cpm = calls_per_month or config.calls_per_month or 1000

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

    call_diffs = compute_diff(old_calls_map, new_calls_map, engine, effective_cpm, config)

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
        assumptions=[f"{effective_cpm} calls/month per call site"],
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
