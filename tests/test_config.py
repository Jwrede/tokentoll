import tempfile
from pathlib import Path

from tokentoll.config import (
    PathOverride,
    ProjectConfig,
    _parse_simple_yaml,
    is_excluded,
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


def test_parse_yaml_skip_dynamic_models():
    text = """
skip_dynamic_models: true
overrides:
  - path: src/strict/
    skip_dynamic_models: true
  - path: src/loose/
    skip_dynamic_models: false
"""
    data = _parse_simple_yaml(text)
    assert data["skip_dynamic_models"] is True
    assert data["overrides"][0]["skip_dynamic_models"] is True
    assert data["overrides"][1]["skip_dynamic_models"] is False


def test_load_config_skip_dynamic_models():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text("skip_dynamic_models: true\n")
        config = load_config(Path(tmpdir))
        assert config.skip_dynamic_models is True


def test_resolve_for_path_skip_dynamic_models_override():
    config = ProjectConfig(
        skip_dynamic_models=False,
        overrides=[
            PathOverride(path="src/strict", skip_dynamic_models=True),
        ],
    )
    resolved_strict = resolve_for_path(config, "src/strict/file.py")
    assert resolved_strict.skip_dynamic_models is True

    resolved_default = resolve_for_path(config, "src/other/file.py")
    assert resolved_default.skip_dynamic_models is False


def test_resolve_for_path_skip_dynamic_models_disabled_by_override():
    config = ProjectConfig(
        skip_dynamic_models=True,
        overrides=[
            PathOverride(path="src/loose", skip_dynamic_models=False),
        ],
    )
    resolved = resolve_for_path(config, "src/loose/file.py")
    assert resolved.skip_dynamic_models is False


def test_parse_yaml_exclude_list():
    text = """
exclude:
  - tests/
  - examples/
  - docs/
"""
    data = _parse_simple_yaml(text)
    assert data["exclude"] == ["tests/", "examples/", "docs/"]


def test_load_config_exclude():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text("exclude:\n  - tests/\n  - examples/\n")
        config = load_config(Path(tmpdir))
        assert config.exclude == ["tests/", "examples/"]


def test_is_excluded_prefix_match():
    config = ProjectConfig(exclude=["tests/", "examples/"])
    assert is_excluded(config, "tests/test_main.py") is True
    assert is_excluded(config, "tests/deep/nested.py") is True
    assert is_excluded(config, "examples/demo.py") is True
    assert is_excluded(config, "src/main.py") is False


def test_is_excluded_glob_match():
    config = ProjectConfig(exclude=["*_test.py", "test_*"])
    assert is_excluded(config, "src/handler_test.py") is True
    assert is_excluded(config, "test_utils.py") is True
    assert is_excluded(config, "src/handler.py") is False


def test_is_excluded_with_project_root():
    config = ProjectConfig(
        exclude=["tests/"],
        project_root="/home/user/project",
    )
    assert is_excluded(config, "/home/user/project/tests/test_main.py") is True
    assert is_excluded(config, "/home/user/project/src/main.py") is False


def test_is_excluded_nested_component_match():
    config = ProjectConfig(exclude=["tests/", "examples/"])
    assert is_excluded(config, "python/tests/test_main.py") is True
    assert is_excluded(config, "src/pkg/examples/demo.py") is True
    assert is_excluded(config, "src/pkg/main.py") is False


def test_is_excluded_empty():
    config = ProjectConfig(exclude=[], use_default_excludes=False)
    assert is_excluded(config, "tests/test_main.py") is False


def test_default_excludes_apply_with_no_user_config():
    config = ProjectConfig()
    assert is_excluded(config, "tests/test_main.py") is True
    assert is_excluded(config, "examples/demo.py") is True
    assert is_excluded(config, "docs/conf.py") is True
    assert is_excluded(config, "cookbook/snippet.py") is True
    assert is_excluded(config, "evals/run.py") is True
    assert is_excluded(config, "scripts/migrate.py") is True
    assert is_excluded(config, "src/main.py") is False


def test_default_excludes_match_nested_paths():
    config = ProjectConfig()
    assert is_excluded(config, "python/tests/test_main.py") is True
    assert is_excluded(config, "src/pkg/examples/demo.py") is True


def test_use_default_excludes_false_disables_defaults():
    config = ProjectConfig(use_default_excludes=False)
    assert is_excluded(config, "tests/test_main.py") is False
    assert is_excluded(config, "examples/demo.py") is False


def test_use_default_excludes_false_keeps_user_excludes():
    config = ProjectConfig(
        exclude=["internal/"],
        use_default_excludes=False,
    )
    assert is_excluded(config, "internal/foo.py") is True
    assert is_excluded(config, "tests/test_main.py") is False


def test_user_excludes_merge_with_defaults():
    config = ProjectConfig(exclude=["vendor/", "generated/"])
    assert is_excluded(config, "tests/test_main.py") is True
    assert is_excluded(config, "vendor/lib.py") is True
    assert is_excluded(config, "generated/code.py") is True
    assert is_excluded(config, "src/main.py") is False


def test_load_config_use_default_excludes_false():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text("use_default_excludes: false\n")
        config = load_config(Path(tmpdir))
        assert config.use_default_excludes is False
        assert is_excluded(config, "tests/test_main.py") is False


def test_load_config_default_excludes_on_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
        assert config.use_default_excludes is True


def test_load_config_policy_budgets_and_rules():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text(
            "budgets:\n"
            "  max_monthly_delta_usd: 250\n"
            "  max_callsite_monthly_usd: 100\n"
            "  max_relative_increase: 5.0\n"
            "policies:\n"
            "  block_unknown_models: true\n"
            "  fail_on_policy_violation: true\n"
        )
        config = load_config(Path(tmpdir))
        assert config.policy.budgets.max_monthly_delta_usd == 250.0
        assert config.policy.budgets.max_callsite_monthly_usd == 100.0
        assert config.policy.budgets.max_relative_increase == 5.0
        assert config.policy.rules.block_unknown_models is True
        assert config.policy.rules.fail_on_policy_violation is True


def test_load_config_partial_policy():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".tokentoll.yml"
        config_path.write_text("budgets:\n  max_monthly_delta_usd: 50\n")
        config = load_config(Path(tmpdir))
        assert config.policy.budgets.max_monthly_delta_usd == 50.0
        assert config.policy.budgets.max_callsite_monthly_usd is None
        assert config.policy.rules.block_unknown_models is False


def test_policy_is_empty_default():
    from tokentoll.config import Policy

    assert Policy().is_empty() is True


def test_policy_is_empty_with_threshold():
    from tokentoll.config import Policy, PolicyBudgets

    p = Policy(budgets=PolicyBudgets(max_monthly_delta_usd=1.0))
    assert p.is_empty() is False
