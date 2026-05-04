from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PathOverride:
    path: str
    default_model: str | None = None
    default_models: dict[str, str] = field(default_factory=dict)
    calls_per_month: int | None = None
    skip_dynamic_models: bool | None = None


@dataclass
class ProjectConfig:
    default_model: str | None = None
    default_models: dict[str, str] = field(default_factory=dict)
    calls_per_month: int | None = None
    skip_dynamic_models: bool = False
    overrides: list[PathOverride] = field(default_factory=list)
    project_root: str | None = None


@dataclass
class ResolvedConfig:
    default_model: str | None = None
    default_models: dict[str, str] = field(default_factory=dict)
    calls_per_month: int | None = None
    skip_dynamic_models: bool = False


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
    dms = dict(config.default_models)
    cpm = config.calls_per_month
    skip = config.skip_dynamic_models
    if best:
        if best.default_model is not None:
            dm = best.default_model
        dms.update(best.default_models)
        if best.calls_per_month is not None:
            cpm = best.calls_per_month
        if best.skip_dynamic_models is not None:
            skip = best.skip_dynamic_models

    return ResolvedConfig(
        default_model=dm,
        default_models=dms,
        calls_per_month=cpm,
        skip_dynamic_models=skip,
    )


def _parse_config_file(path: Path) -> ProjectConfig:
    text = path.read_text(encoding="utf-8")
    data = _parse_simple_yaml(text)
    config = _data_to_config(data)
    config.project_root = str(path.resolve().parent)
    return config


def _parse_default_models(data: dict) -> dict[str, str]:
    raw = data.get("default_models")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items() if v is not None}
    return {}


def _data_to_config(data: dict) -> ProjectConfig:
    dm = data.get("default_model")
    dms = _parse_default_models(data)
    cpm = data.get("calls_per_month")
    if cpm is not None:
        cpm = int(cpm)
    skip = bool(data.get("skip_dynamic_models", False))

    overrides: list[PathOverride] = []
    for item in data.get("overrides", []):
        if isinstance(item, dict) and "path" in item:
            o_cpm = item.get("calls_per_month")
            o_skip = item.get("skip_dynamic_models")
            overrides.append(
                PathOverride(
                    path=str(item["path"]),
                    default_model=item.get("default_model"),
                    default_models=_parse_default_models(item),
                    calls_per_month=int(o_cpm) if o_cpm is not None else None,
                    skip_dynamic_models=bool(o_skip) if o_skip is not None else None,
                )
            )

    return ProjectConfig(
        default_model=dm,
        default_models=dms,
        calls_per_month=cpm,
        skip_dynamic_models=skip,
        overrides=overrides,
    )


_KV_RE = re.compile(r"^(\w[\w_]*):\s*(.+)$")


def _parse_simple_yaml(text: str) -> dict:
    """Minimal YAML subset parser for .tokentoll.yml.

    Handles: top-level scalars, nested dicts (one level), and lists of dicts.
    """
    result: dict = {}
    current_block_key: str | None = None
    current_block_is_list = False
    current_item: dict | None = None
    lines = text.split("\n")

    for line in lines:
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        if indent > 0 and current_block_key is not None:
            # List item start
            if stripped.lstrip().startswith("- "):
                current_block_is_list = True
                if current_item is not None:
                    result.setdefault(current_block_key, []).append(current_item)
                content = stripped.lstrip()[2:].strip()
                current_item = {}
                m = _KV_RE.match(content)
                if m:
                    current_item[m.group(1)] = _parse_scalar(m.group(2))
                continue

            # Continuation of a list item (deeper indent)
            if current_block_is_list and current_item is not None and indent >= 4:
                m = _KV_RE.match(stripped.strip())
                if m:
                    current_item[m.group(1)] = _parse_scalar(m.group(2))
                continue

            # Nested dict value (not a list)
            if not current_block_is_list:
                m = _KV_RE.match(stripped.strip())
                if m:
                    if not isinstance(result.get(current_block_key), dict):
                        result[current_block_key] = {}
                    result[current_block_key][m.group(1)] = _parse_scalar(m.group(2))
                continue

        # Flush pending list item before processing top-level key
        if current_item is not None and current_block_key is not None:
            result.setdefault(current_block_key, []).append(current_item)
            current_item = None

        if indent == 0:
            current_block_is_list = False
            m = _KV_RE.match(stripped)
            if m:
                key, val = m.group(1), m.group(2).strip()
                current_block_key = None
                result[key] = _parse_scalar(val)
            elif stripped.endswith(":"):
                current_block_key = stripped[:-1].strip()
                current_item = None

    if current_item is not None and current_block_key is not None:
        result.setdefault(current_block_key, []).append(current_item)

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
