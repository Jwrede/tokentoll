from tokentoll.core.models import CallType, ChangeType, LLMCall
from tokentoll.diff.engine import compute_diff
from tokentoll.pricing.engine import PricingEngine


def _make_call(
    model: str,
    line: int = 1,
    sdk: str = "openai",
    fpath: str = "test.py",
    max_tokens: int | None = 1000,
) -> LLMCall:
    return LLMCall(
        file_path=fpath,
        line_number=line,
        sdk=sdk,
        call_type=CallType.CHAT_COMPLETION,
        model=model,
        model_is_literal=True,
        max_tokens=max_tokens,
        estimated_output_tokens=max_tokens,
        raw_expression="client.chat.completions.create",
    )


def test_added_call():
    engine = PricingEngine()
    old: dict[str, list] = {}
    new = {"test.py": [_make_call("gpt-4o", line=10)]}
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.ADDED
    assert diffs[0].new_call is not None
    assert diffs[0].monthly_delta is not None
    assert diffs[0].monthly_delta > 0


def test_removed_call():
    engine = PricingEngine()
    old = {"test.py": [_make_call("gpt-4o", line=10)]}
    new: dict[str, list] = {}
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.REMOVED
    assert diffs[0].monthly_delta is not None
    assert diffs[0].monthly_delta < 0


def test_model_swap():
    engine = PricingEngine()
    old = {"test.py": [_make_call("gpt-4o", line=10)]}
    new = {"test.py": [_make_call("gpt-4o-mini", line=10)]}
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.MODIFIED
    assert diffs[0].monthly_delta is not None
    assert diffs[0].monthly_delta < 0


def test_no_changes():
    engine = PricingEngine()
    call = _make_call("gpt-4o", line=10)
    old = {"test.py": [call]}
    new = {"test.py": [call]}
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 0


def test_multiple_files():
    engine = PricingEngine()
    old = {
        "a.py": [_make_call("gpt-4o", line=5, fpath="a.py")],
    }
    new = {
        "a.py": [_make_call("gpt-4o", line=5, fpath="a.py")],
        "b.py": [_make_call("gpt-4o-mini", line=1, fpath="b.py")],
    }
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.ADDED
