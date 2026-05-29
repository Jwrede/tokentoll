"""End-to-end JS/TS scanner tests using fixture files."""

from __future__ import annotations

from pathlib import Path

from tokentoll.core.models import CallType
from tokentoll.scanner import scan_paths, scan_source
from tokentoll.scanner.js_scanner import build_variable_map, parse

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "js"


def _scan_fixture(name: str):
    path = FIXTURE_DIR / name
    return scan_source(path.read_text(), str(path))


def test_openai_literal_model():
    calls = _scan_fixture("openai_literal.ts")
    assert len(calls) == 1
    c = calls[0]
    assert c.sdk == "openai"
    assert c.call_type == CallType.CHAT_COMPLETION
    assert c.model == "gpt-4o"
    assert c.model_is_literal is True
    assert c.max_tokens == 1024


def test_openai_constant_model_and_max_tokens():
    calls = _scan_fixture("openai_constant.ts")
    assert len(calls) == 1
    c = calls[0]
    assert c.sdk == "openai"
    assert c.model == "gpt-4o-mini"
    assert c.model_is_literal is False
    assert c.max_tokens == 512


def test_openai_env_fallback_or():
    calls = _scan_fixture("openai_env_fallback.ts")
    assert len(calls) == 2
    chat_call = next(c for c in calls if c.line_number < 10)
    assert chat_call.model == "gpt-4o"
    nullish_call = next(c for c in calls if c.line_number > 10)
    assert nullish_call.model == "gpt-4o-mini"


def test_anthropic_messages_create():
    calls = _scan_fixture("anthropic.ts")
    assert len(calls) == 2
    create_call = next(c for c in calls if "create" in c.raw_expression)
    assert create_call.sdk == "anthropic"
    assert create_call.model == "claude-sonnet-4-20250514"
    assert create_call.max_tokens == 4096

    stream_call = next(c for c in calls if "stream" in c.raw_expression)
    assert stream_call.sdk == "anthropic"
    assert stream_call.model == "claude-haiku-3-5-20241022"
    assert stream_call.max_tokens == 2048


def test_vercel_generate_with_provider_wrappers():
    calls = _scan_fixture("vercel_generate.ts")
    assert len(calls) == 2
    openai_call = next(c for c in calls if c.sdk == "openai")
    assert openai_call.model == "gpt-4o"
    assert openai_call.max_tokens == 1024
    anthropic_call = next(c for c in calls if c.sdk == "anthropic")
    assert anthropic_call.model == "claude-sonnet-4-5"


def test_vercel_stream_and_embed():
    calls = _scan_fixture("vercel_stream.ts")
    assert len(calls) == 2
    stream_call = next(c for c in calls if c.call_type == CallType.CHAT_COMPLETION)
    assert stream_call.sdk == "openai"
    assert stream_call.model == "gpt-4o-mini"
    assert stream_call.max_tokens == 4096
    embed_call = next(c for c in calls if c.call_type == CallType.EMBEDDING)
    assert embed_call.sdk == "openai"
    assert embed_call.model == "text-embedding-3-small"


def test_langchain_constructors():
    calls = _scan_fixture("langchain.ts")
    assert len(calls) == 3
    openai = next(c for c in calls if c.sdk == "openai")
    assert openai.model == "gpt-4o"
    assert openai.max_tokens == 2048
    anthropic = next(c for c in calls if c.sdk == "anthropic")
    assert anthropic.model == "claude-haiku-3-5-20241022"
    google = next(c for c in calls if c.sdk == "google_genai")
    assert google.model == "gemini-2.0-flash"


def test_dynamic_model_produces_call_with_none():
    calls = _scan_fixture("dynamic_warning.ts")
    assert len(calls) == 1
    c = calls[0]
    assert c.sdk == "openai"
    assert c.model is None
    assert c.model_is_literal is False


def test_tsx_file_parses_and_detects():
    calls = _scan_fixture("nextjs_api_route.tsx")
    assert len(calls) == 1
    c = calls[0]
    assert c.sdk == "openai"
    assert c.model == "gpt-4o-mini"
    assert c.max_tokens == 800


def test_openai_compatible_client_detected_as_openai():
    calls = _scan_fixture("openai_compatible.ts")
    assert len(calls) == 1
    c = calls[0]
    assert c.sdk == "openai"
    assert c.model == "llama-3.3-70b-versatile"


def test_scan_paths_walks_js_and_ts():
    calls = scan_paths([str(FIXTURE_DIR)])
    # Every fixture should produce at least one call.
    sdks = {c.sdk for c in calls}
    assert "openai" in sdks
    assert "anthropic" in sdks
    assert "google_genai" in sdks
    assert len(calls) >= 14


def test_variable_map_resolves_constants_and_objects():
    source = b"""
const MODEL = "gpt-4o";
const config = { model: "gpt-4o-mini", maxTokens: 512 };
function f(model = "claude-sonnet-4-5") { return model; }
const fallback = process.env.X || "gpt-4o-mini";
"""
    tree = parse(source, "x.ts")
    assert tree is not None
    vars_map = build_variable_map(tree.root_node, source)
    assert vars_map["MODEL"] == "gpt-4o"
    assert vars_map["config.model"] == "gpt-4o-mini"
    assert vars_map["config.maxTokens"] == 512
    assert vars_map["model"] == "claude-sonnet-4-5"
    assert vars_map["fallback"] == "gpt-4o-mini"


def test_scan_source_returns_empty_for_unrelated_ts():
    calls = scan_source("export const x = 1;\n", "/tmp/x.ts")
    assert calls == []


def test_scan_source_returns_empty_for_unsupported_extension():
    calls = scan_source('foo("gpt-4o")', "/tmp/x.rs")
    assert calls == []


def test_vercel_detector_ignores_method_calls():
    """Cohere/Ollama/IBM client methods named embed() must not be claimed
    by the Vercel AI SDK detector.

    Regression for v0.8 dogfood: scanning langchainjs surfaced false
    positives in langchain-cohere/embeddings.ts (`this.client.embed(req)`)
    because the Vercel detector accepted any member-expression callee
    ending in embed/embedMany/generateText/streamText.
    """
    calls = _scan_fixture("cohere_embed_not_vercel.ts")
    # No Vercel AI SDK detections — this file imports cohere-ai, not @ai-sdk.
    assert all(c.sdk != "vercel_ai_sdk" for c in calls)


def test_this_chain_call():
    """Member chains rooted at `this` (and `super`) must resolve.

    Regression for v0.8 dogfood: anthropic-sdk-typescript and similar
    class-based clients use `this.client.messages.create(...)` which
    previously slipped through the detector because member_expression_path
    only accepted identifier bases.
    """
    calls = _scan_fixture("this_chain.ts")
    assert len(calls) == 2
    create = next(c for c in calls if c.model == "claude-sonnet-4-5")
    assert create.sdk == "anthropic"
    assert create.max_tokens == 2048
    beta = next(c for c in calls if c.model == "claude-haiku-3-5-20241022")
    assert beta.sdk == "anthropic"
    assert beta.max_tokens == 1024


def test_ts_wrapper_unwrapping():
    """TS-only wrappers (as, satisfies, !, parens, <T>) must not hide values.

    Regression for v0.8 dogfood: chatbot-ui and similar TS apps wrap call
    arguments with `as Foo`, which left the resolver returning None and
    obscured real model names.
    """
    calls = _scan_fixture("ts_wrappers.ts")
    assert len(calls) == 5

    by_line = {c.line_number: c for c in calls}

    as_call = next(
        c
        for c in calls
        if "asCast" not in c.raw_expression and c.model == "gpt-4o-mini" and c.max_tokens == 1024
    )
    assert as_call.model_is_literal is True

    satisfies_call = next(c for c in calls if c.model == "gpt-4o" and c.max_tokens is None)
    assert satisfies_call.model_is_literal is True

    non_null_call = next(
        c
        for c in by_line.values()
        if c.model == "gpt-4o" and c.max_tokens is None and c is not satisfies_call
    )
    # MODEL! resolves through the variable map; not a string literal in the call args.
    assert non_null_call.model_is_literal is False

    parens_calls = [c for c in calls if c.model == "gpt-4o-mini"]
    assert len(parens_calls) == 2

    legacy_call = next(c for c in calls if c.model == "claude-not-really")
    assert legacy_call.model_is_literal is True
