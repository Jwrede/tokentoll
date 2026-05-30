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


def test_identical_call_shifted_far_is_unchanged():
    # A refactor that pushes an existing call site below the line-proximity
    # window must not surface it as REMOVED + ADDED.
    engine = PricingEngine()
    old = {"test.py": [_make_call("gpt-4o", line=10)]}
    new = {"test.py": [_make_call("gpt-4o", line=200)]}
    diffs = compute_diff(old, new, engine, 1000)
    assert diffs == []


def test_many_identical_calls_shifted_far_are_all_unchanged():
    # Reproduces the gpt-researcher case: a file with many same-shape calls
    # that shift around during a refactor. Currently produces N phantom
    # REMOVED + N phantom ADDED pairs.
    engine = PricingEngine()
    old = {
        "base.py": [
            _make_call("gpt-4o", line=145),
            _make_call("gpt-4o", line=160),
            _make_call("gpt-4o", line=278),
            _make_call("gpt-4o", line=286),
            _make_call("gpt-4o", line=294),
        ]
    }
    new = {
        "base.py": [
            _make_call("gpt-4o", line=108),
            _make_call("gpt-4o", line=113),
            _make_call("gpt-4o", line=184),
            _make_call("gpt-4o", line=197),
            _make_call("gpt-4o", line=259),
        ]
    }
    diffs = compute_diff(old, new, engine, 1000)
    assert diffs == []


def test_model_swap_with_line_shift_still_detected():
    # A real cost change should still be caught even when surrounding code
    # shifted the call site, provided no identical-shape decoy is nearby.
    engine = PricingEngine()
    old = {"test.py": [_make_call("gpt-4o-mini", line=10)]}
    new = {"test.py": [_make_call("gpt-4o", line=12)]}
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.MODIFIED


def test_unchanged_calls_do_not_consume_modified_match():
    # If there are 2 identical calls and 1 model-swap call in a file, the
    # 2 identical pairs should be matched first so the model swap surfaces
    # as MODIFIED rather than getting paired with one of the identical calls.
    engine = PricingEngine()
    old = {
        "test.py": [
            _make_call("gpt-4o", line=10),
            _make_call("gpt-4o", line=20),
            _make_call("gpt-4o-mini", line=30),
        ]
    }
    new = {
        "test.py": [
            _make_call("gpt-4o", line=10),
            _make_call("gpt-4o", line=20),
            _make_call("gpt-4o", line=30),
        ]
    }
    diffs = compute_diff(old, new, engine, 1000)
    assert len(diffs) == 1
    assert diffs[0].change_type == ChangeType.MODIFIED
    assert diffs[0].old_call.model == "gpt-4o-mini"
    assert diffs[0].new_call.model == "gpt-4o"
