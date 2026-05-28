"""Mixed Python + TypeScript scan."""

from __future__ import annotations

from pathlib import Path

from tokentoll.scanner import scan_paths

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mixed_repo"


def test_mixed_repo_scan_includes_both_languages():
    calls = scan_paths([str(FIXTURE_DIR)])
    file_exts = {Path(c.file_path).suffix for c in calls}
    assert ".py" in file_exts
    assert ".ts" in file_exts

    py_call = next(c for c in calls if c.file_path.endswith(".py"))
    assert py_call.sdk == "openai"
    assert py_call.model == "gpt-4o"

    ts_call = next(c for c in calls if c.file_path.endswith(".ts"))
    assert ts_call.sdk == "openai"
    assert ts_call.model == "gpt-4o-mini"
