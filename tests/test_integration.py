import os
import subprocess
import textwrap

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with LLM calls."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


@pytest.mark.integration
def test_scan_finds_calls(git_repo):
    code = textwrap.dedent("""\
        from openai import OpenAI
        client = OpenAI()
        client.chat.completions.create(model="gpt-4o", max_tokens=1000, messages=[])
    """)
    (git_repo / "app.py").write_text(code)

    from tokentoll.scanner.python_scanner import scan_paths

    calls = scan_paths([str(git_repo)])
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


@pytest.mark.integration
def test_diff_detects_model_swap(git_repo):
    code_v1 = textwrap.dedent("""\
        from openai import OpenAI
        client = OpenAI()
        client.chat.completions.create(model="gpt-4o", max_tokens=1000, messages=[])
    """)
    (git_repo / "app.py").write_text(code_v1)
    subprocess.run(["git", "add", "app.py"], cwd=git_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "v1"],
        cwd=git_repo,
        capture_output=True,
        check=True,
    )

    code_v2 = textwrap.dedent("""\
        from openai import OpenAI
        client = OpenAI()
        client.chat.completions.create(model="gpt-4o-mini", max_tokens=1000, messages=[])
    """)
    (git_repo / "app.py").write_text(code_v2)
    subprocess.run(["git", "add", "app.py"], cwd=git_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "v2"],
        cwd=git_repo,
        capture_output=True,
        check=True,
    )

    from tokentoll.core.models import ChangeType
    from tokentoll.diff.engine import compute_diff
    from tokentoll.diff.git import get_changed_files, get_file_at_ref
    from tokentoll.pricing.engine import PricingEngine
    from tokentoll.scanner.python_scanner import scan_source

    old_cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        changed = get_changed_files("HEAD~1", "HEAD")
        assert len(changed) == 1

        old_src = get_file_at_ref("HEAD~1", "app.py")
        new_src = get_file_at_ref("HEAD", "app.py")
        assert old_src is not None
        assert new_src is not None

        old_calls = {"app.py": scan_source(old_src, "app.py")}
        new_calls = {"app.py": scan_source(new_src, "app.py")}

        engine = PricingEngine()
        diffs = compute_diff(old_calls, new_calls, engine, 1000)
        assert len(diffs) == 1
        assert diffs[0].change_type == ChangeType.MODIFIED
        assert diffs[0].old_call.model == "gpt-4o"
        assert diffs[0].new_call.model == "gpt-4o-mini"
        assert diffs[0].monthly_delta < 0
    finally:
        os.chdir(old_cwd)


@pytest.mark.integration
def test_diff_detects_added_call(git_repo):
    (git_repo / "app.py").write_text("# empty\n")
    subprocess.run(["git", "add", "app.py"], cwd=git_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "v1"],
        cwd=git_repo,
        capture_output=True,
        check=True,
    )

    code = textwrap.dedent("""\
        from anthropic import Anthropic
        client = Anthropic()
        client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1024, messages=[])
    """)
    (git_repo / "app.py").write_text(code)
    subprocess.run(["git", "add", "app.py"], cwd=git_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "v2"],
        cwd=git_repo,
        capture_output=True,
        check=True,
    )

    from tokentoll.core.models import ChangeType
    from tokentoll.diff.engine import compute_diff
    from tokentoll.diff.git import get_file_at_ref
    from tokentoll.pricing.engine import PricingEngine
    from tokentoll.scanner.python_scanner import scan_source

    old_cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        old_src = get_file_at_ref("HEAD~1", "app.py")
        new_src = get_file_at_ref("HEAD", "app.py")

        old_calls = {"app.py": scan_source(old_src, "app.py")}
        new_calls = {"app.py": scan_source(new_src, "app.py")}

        engine = PricingEngine()
        diffs = compute_diff(old_calls, new_calls, engine, 1000)
        assert len(diffs) == 1
        assert diffs[0].change_type == ChangeType.ADDED
        assert diffs[0].monthly_delta > 0
    finally:
        os.chdir(old_cwd)
