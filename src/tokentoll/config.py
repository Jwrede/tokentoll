from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PathOverride:
    path: str
    default_model: str | None = None
    calls_per_month: int | None = None


@dataclass
class ProjectConfig:
    default_model: str | None = None
    calls_per_month: int | None = None
    overrides: list[PathOverride] = field(default_factory=list)
    project_root: str | None = None


@dataclass
class ResolvedConfig:
    default_model: str | None = None
    calls_per_month: int | None = None


_CONFIG_FILENAME = ".tokentoll.yml"


def load_config(search_from: Path | None = None) -> ProjectConfig:
    """Find and load .tokentoll.yml by walking up from search_from."""
    if search_from is None:
        search_from = Path.cwd()
    search_from = search_from.resolve()

    current = search_from if search_from.is_dir() else search_from.parent
    while True:
        candidate = current / _CONFIG_FILENAME
        if candidate.is_file():
            return _parse_config_file(candidate)
        parent = current.parent
        if parent == current:
            break
        current = parent

    return ProjectConfig()


def resolve_for_path(config: ProjectConfig, file_path: str) -> ResolvedConfig:
    """Resolve config for a specific file path using longest-prefix matching."""
    best: PathOverride | None = None
    best_len = -1

    normalized = file_path.replace("\\", "/")
    # Make file_path relative to project root for matching
    if config.project_root:
        root = config.project_root.replace("\\", "/").rstrip("/") + "/"
        if normalized.startswith(root):
            normalized = normalized[len(root) :]

    for override in config.overrides:
        prefix = override.path.replace("\\", "/").rstrip("/")
        if normalized == prefix or normalized.startswith(prefix + "/"):
            if len(prefix) > best_len:
                best = override
                best_len = len(prefix)

    dm = config.default_model
    cpm = config.calls_per_month
    if best:
        if best.default_model is not None:
            dm = best.default_model
        if best.calls_per_month is not None:
            cpm = best.calls_per_month

    return ResolvedConfig(default_model=dm, calls_per_month=cpm)


def _parse_config_file(path: Path) -> ProjectConfig:
    text = path.read_text(encoding="utf-8")
    data = _parse_simple_yaml(text)
    config = _data_to_config(data)
    config.project_root = str(path.resolve().parent)
    return config


def _data_to_config(data: dict) -> ProjectConfig:
    dm = data.get("default_model")
    cpm = data.get("calls_per_month")
    if cpm is not None:
        cpm = int(cpm)

    overrides: list[PathOverride] = []
    for item in data.get("overrides", []):
        if isinstance(item, dict) and "path" in item:
            o_cpm = item.get("calls_per_month")
            overrides.append(
                PathOverride(
                    path=str(item["path"]),
                    default_model=item.get("default_model"),
                    calls_per_month=int(o_cpm) if o_cpm is not None else None,
                )
            )

    return ProjectConfig(default_model=dm, calls_per_month=cpm, overrides=overrides)


_KV_RE = re.compile(r"^(\w[\w_]*):\s*(.+)$")


def _parse_simple_yaml(text: str) -> dict:
    """Minimal YAML subset parser for .tokentoll.yml.

    Handles: top-level key: value, list items (- key: value), one level of nesting.
    """
    result: dict = {}
    current_list_key: str | None = None
    current_item: dict | None = None
    lines = text.split("\n")

    for line in lines:
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        # List item: "  - key: value" or "    key: value" continuation
        if stripped.lstrip().startswith("- "):
            if current_list_key is None:
                continue
            if current_item is not None:
                result.setdefault(current_list_key, []).append(current_item)
            content = stripped.lstrip()[2:].strip()
            current_item = {}
            m = _KV_RE.match(content)
            if m:
                current_item[m.group(1)] = _parse_scalar(m.group(2))
            continue

        if indent >= 4 and current_item is not None:
            m = _KV_RE.match(stripped.strip())
            if m:
                current_item[m.group(1)] = _parse_scalar(m.group(2))
            continue

        # Flush pending list item
        if current_item is not None and current_list_key is not None:
            result.setdefault(current_list_key, []).append(current_item)
            current_item = None

        if indent == 0:
            m = _KV_RE.match(stripped)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val == "" or val == "[]":
                    current_list_key = key
                    result[key] = []
                else:
                    current_list_key = None
                    result[key] = _parse_scalar(val)
            elif stripped.endswith(":"):
                current_list_key = stripped[:-1].strip()
                result.setdefault(current_list_key, [])

    if current_item is not None and current_list_key is not None:
        result.setdefault(current_list_key, []).append(current_item)

    return result


def _parse_scalar(val: str) -> str | int | float | None:
    if val in ("null", "~", ""):
        return None
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    # Strip quotes
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        return val[1:-1]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val
