"""Scanner package: routes file scanning to language-specific scanners.

Public entry points (used by core/pipeline.py and tests):
- scan_paths(paths): walk paths, scan each file by extension
- scan_source(source, file_path): scan a single source string, language
  inferred from file_path extension
"""

from __future__ import annotations

from pathlib import Path

from tokentoll.core.models import LLMCall

_PY_EXTS = {".py"}
_JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}


def scan_source(source: str, file_path: str) -> list[LLMCall]:
    """Scan a single source string. Language inferred from file extension."""
    ext = Path(file_path).suffix
    if ext in _PY_EXTS:
        from tokentoll.scanner.python_scanner import scan_source as _scan_py

        return _scan_py(source, file_path)
    if ext in _JS_EXTS:
        from tokentoll.scanner.js_scanner import scan_source_js

        return scan_source_js(source, file_path)
    return []


def scan_file(path: Path) -> list[LLMCall]:
    ext = path.suffix
    if ext in _PY_EXTS:
        from tokentoll.scanner.python_scanner import scan_file as _scan_py_file

        return _scan_py_file(path)
    if ext in _JS_EXTS:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        return scan_source(source, str(path))
    return []


def scan_paths(paths: list[str]) -> list[LLMCall]:
    """Walk paths and scan every supported source file found."""
    all_calls: list[LLMCall] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix in (_PY_EXTS | _JS_EXTS):
            all_calls.extend(scan_file(path))
        elif path.is_dir():
            for ext in sorted(_PY_EXTS | _JS_EXTS):
                for src_file in sorted(path.rglob(f"*{ext}")):
                    all_calls.extend(scan_file(src_file))
    return all_calls
