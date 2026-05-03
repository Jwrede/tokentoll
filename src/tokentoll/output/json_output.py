from __future__ import annotations

from tokentoll.core.models import CostEstimate, DiffReport, ScanReport


def _estimate_to_dict(est: CostEstimate) -> dict:
    return {
        "file_path": est.call.file_path,
        "line_number": est.call.line_number,
        "sdk": est.call.sdk,
        "call_type": est.call.call_type.value,
        "model": est.call.model,
        "model_is_literal": est.call.model_is_literal,
        "max_tokens": est.call.max_tokens,
        "estimated_input_tokens": est.call.estimated_input_tokens,
        "estimated_output_tokens": est.call.estimated_output_tokens,
        "model_found": est.model_found,
        "used_default_model": est.used_default_model,
        "estimated_cost_per_call": est.estimated_cost_per_call,
        "monthly_estimate": est.monthly_estimate,
        "notes": est.notes,
    }


def format_scan_report_json(report: ScanReport) -> dict:
    return {
        "calls": [_estimate_to_dict(est) for est in report.estimates],
        "total_monthly_estimate": report.total_monthly_estimate,
        "assumptions": report.assumptions,
        "warnings": report.warnings,
    }


def format_diff_report_json(report: DiffReport) -> dict:
    diffs = []
    for d in report.call_diffs:
        if d.change_type.value == "unchanged":
            continue
        entry: dict = {
            "change_type": d.change_type.value,
            "monthly_delta": d.monthly_delta,
            "cost_delta_per_call": d.cost_delta_per_call,
        }
        if d.new_call:
            entry["new"] = {
                "file_path": d.new_call.file_path,
                "line_number": d.new_call.line_number,
                "sdk": d.new_call.sdk,
                "model": d.new_call.model,
            }
        if d.old_call:
            entry["old"] = {
                "file_path": d.old_call.file_path,
                "line_number": d.old_call.line_number,
                "sdk": d.old_call.sdk,
                "model": d.old_call.model,
            }
        diffs.append(entry)

    return {
        "base_ref": report.base_ref,
        "head_ref": report.head_ref,
        "diffs": diffs,
        "total_monthly_delta": report.total_monthly_delta,
        "total_calls_added": report.total_calls_added,
        "total_calls_removed": report.total_calls_removed,
        "total_calls_modified": report.total_calls_modified,
        "assumptions": report.assumptions,
        "warnings": report.warnings,
    }
