import tempfile
from pathlib import Path

from tokentoll.config import (
    PathOverride,
    ProjectConfig,
    _parse_simple_yaml,
    load_config,
    resolve_for_path,
)


def test_parse_simple_yaml_scalars():
    text = """
default_model: gpt-4o
calls_per_month: 5000
"""
    data = _parse_simple_yaml(text)
    assert data["default_model"] == "gpt-4o"
    assert data["calls_per_month"] == 5000


def test_parse_simple_yaml_with_overrides():
    text = """
default_model: gpt-4o
overrides:
  - path: src/agents/
    default_model: claude-sonnet-4-20250514
    calls_per_month: 10000
  - path: src/embeddings/
    default_model: text-embedding-3-small
"""
    data = _parse_simple_yaml(text)
    assert data["default_model"] == "gpt-4o"
    assert len(data["overrides"]) == 2
    assert data["overrides"][0]["path"] == "src/agents/"
    assert data["overrides"][0]["default_model"] == "claude-sonnet-4-20250514"
    assert data["overrides"][0]["calls_per_month"] == 10000
    assert data["overrides"][1]["path"] == "src/embeddings/"
    assert data["overrides"][1]["default_model"] == "text-embedding-3-small"


def test_parse_yaml_comments():
    text = """
# Main config
default_model: gpt-4o  # the default
"""
    data = _parse_simple_yaml(text)
    assert data["default_model"] == "gpt-4o"


def test_parse_yaml_quoted_values():
    text = """
default_model: "gpt-4o-mini"
"""
    data = _parse_simple_yaml(text)
    assert data["default_model"] == "gpt-4o-mini"


def test_load_config_finds_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text("default_model: gpt-4o\ncalls_per_month: 2000\n")
        subdir = Path(tmpdir) / "src" / "deep"
        subdir.mkdir(parents=True)

        config = load_config(subdir)
        assert config.default_model == "gpt-4o"
        assert config.calls_per_month == 2000


def test_load_config_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
        assert config.default_model is None
        assert config.calls_per_month is None
        assert config.overrides == []


def test_resolve_for_path_project_default():
    config = ProjectConfig(default_model="gpt-4o", calls_per_month=5000)
    resolved = resolve_for_path(config, "src/main.py")
    assert resolved.default_model == "gpt-4o"
    assert resolved.calls_per_month == 5000


def test_resolve_for_path_override():
    config = ProjectConfig(
        default_model="gpt-4o",
        overrides=[
            PathOverride(path="src/agents", default_model="claude-sonnet-4-20250514"),
        ],
    )
    resolved = resolve_for_path(config, "src/agents/router.py")
    assert resolved.default_model == "claude-sonnet-4-20250514"


def test_resolve_for_path_no_match():
    config = ProjectConfig(
        default_model="gpt-4o",
        overrides=[
            PathOverride(path="src/agents", default_model="claude-sonnet-4-20250514"),
        ],
    )
    resolved = resolve_for_path(config, "src/other/file.py")
    assert resolved.default_model == "gpt-4o"


def test_resolve_for_path_longest_prefix():
    config = ProjectConfig(
        default_model="gpt-4o",
        overrides=[
            PathOverride(path="src", default_model="gpt-4o-mini"),
            PathOverride(path="src/agents", default_model="claude-sonnet-4-20250514"),
        ],
    )
    resolved = resolve_for_path(config, "src/agents/router.py")
    assert resolved.default_model == "claude-sonnet-4-20250514"

    resolved2 = resolve_for_path(config, "src/utils.py")
    assert resolved2.default_model == "gpt-4o-mini"


def test_resolve_for_path_absolute_with_project_root():
    config = ProjectConfig(
        default_model="gpt-4o",
        project_root="/home/user/project",
        overrides=[
            PathOverride(path="src/agents", default_model="claude-sonnet-4-20250514"),
        ],
    )
    resolved = resolve_for_path(config, "/home/user/project/src/agents/router.py")
    assert resolved.default_model == "claude-sonnet-4-20250514"

    resolved2 = resolve_for_path(config, "/home/user/project/src/other.py")
    assert resolved2.default_model == "gpt-4o"


def test_resolve_for_path_calls_per_month_override():
    config = ProjectConfig(
        calls_per_month=1000,
        overrides=[
            PathOverride(path="src/hot", calls_per_month=50000),
        ],
    )
    resolved = resolve_for_path(config, "src/hot/handler.py")
    assert resolved.calls_per_month == 50000

    resolved2 = resolve_for_path(config, "src/cold/batch.py")
    assert resolved2.calls_per_month == 1000
