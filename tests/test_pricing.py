from tokentoll.core.models import CallType, LLMCall
from tokentoll.pricing.engine import PricingEngine


def _make_call(model: str, sdk: str = "openai", max_tokens: int | None = 1000) -> LLMCall:
    return LLMCall(
        file_path="test.py",
        line_number=1,
        sdk=sdk,
        call_type=CallType.CHAT_COMPLETION,
        model=model,
        model_is_literal=True,
        max_tokens=max_tokens,
        estimated_output_tokens=max_tokens,
    )


def test_lookup_exact_model():
    engine = PricingEngine()
    pricing = engine.lookup("gpt-4o")
    assert pricing is not None
    assert pricing.input_cost_per_token is not None
    assert pricing.input_cost_per_token > 0


def test_lookup_with_provider_prefix():
    engine = PricingEngine()
    pricing = engine.lookup("gpt-4o-mini", sdk="openai")
    assert pricing is not None


def test_lookup_unknown_model():
    engine = PricingEngine()
    pricing = engine.lookup("nonexistent-model-xyz")
    assert pricing is None


def test_estimate_known_model():
    engine = PricingEngine()
    call = _make_call("gpt-4o", max_tokens=1000)
    est = engine.estimate(call, calls_per_month=1000)
    assert est.model_found is True
    assert est.estimated_cost_per_call is not None
    assert est.estimated_cost_per_call > 0
    assert est.monthly_estimate is not None
    assert est.monthly_estimate > 0


def test_estimate_unknown_model():
    engine = PricingEngine()
    call = _make_call("nonexistent-model-xyz")
    est = engine.estimate(call, calls_per_month=1000)
    assert est.model_found is False
    assert "Unknown model" in est.notes[0]


def test_estimate_dynamic_model_uses_sdk_default():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(call)
    assert est.model_found is True
    assert est.used_default_model == "gpt-4o"
    assert "dynamic" in est.notes[0].lower()


def test_estimate_anthropic_model():
    engine = PricingEngine()
    call = _make_call("claude-sonnet-4-20250514", sdk="anthropic", max_tokens=1024)
    est = engine.estimate(call, calls_per_month=500)
    assert est.model_found is True
    assert est.monthly_estimate is not None


def test_estimate_dynamic_with_default_model():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(call, default_model="gpt-4o")
    assert est.model_found is True
    assert est.used_default_model == "gpt-4o"
    assert est.estimated_cost_per_call is not None
    assert est.estimated_cost_per_call > 0
    assert any("default" in n.lower() for n in est.notes)


def test_estimate_dynamic_with_bad_default_model():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(call, default_model="nonexistent-model-xyz")
    assert est.model_found is False
    assert "not found" in est.notes[0].lower()


def test_estimate_resolved_model_ignores_default():
    """When model IS resolved, default_model should be ignored."""
    call = _make_call("gpt-4o")
    engine = PricingEngine()
    est = engine.estimate(call, default_model="gpt-4o-mini")
    assert est.used_default_model is None
    assert est.model_found is True


def test_estimate_dynamic_anthropic_uses_claude_default():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="anthropic",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(call)
    assert est.model_found is True
    assert est.used_default_model == "claude-sonnet-4-20250514"


def test_estimate_dynamic_google_uses_gemini_default():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="google_genai",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(call)
    assert est.model_found is True
    assert est.used_default_model == "gemini-2.0-flash"


def test_estimate_per_sdk_config_overrides_builtin():
    call = LLMCall(
        file_path="test.py",
        line_number=1,
        sdk="openai",
        call_type=CallType.CHAT_COMPLETION,
        model=None,
        model_is_literal=False,
        max_tokens=None,
    )
    engine = PricingEngine()
    est = engine.estimate(
        call,
        default_models={"openai": "gpt-4o-mini"},
    )
    assert est.model_found is True
    assert est.used_default_model == "gpt-4o-mini"
