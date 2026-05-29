"""Vercel AI SDK detector for JavaScript/TypeScript.

Matches:
- generateText({ model: openai("gpt-4o"), ... })
- streamText({ model: anthropic("claude-sonnet-4-5"), ... })
- generateObject({ ... })
- streamObject({ ... })
- embed({ model: openai.embedding("text-embedding-3-small") })
- embedMany({ ... })

The provider wrapper call (openai("gpt-4o"), anthropic.chat("..."))
is resolved by js_resolver.resolve_string. SDK is inferred from the
wrapper name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.js.base import BaseJsDetector
from tokentoll.scanner.js_resolver import (
    extract_string_literal,
    find_object_property,
    get_call_arguments,
    member_expression_path,
    node_text,
    resolve_int,
    resolve_string,
    unwrap,
)
from tokentoll.scanner.js_scanner import walk_calls

if TYPE_CHECKING:
    from tree_sitter import Node


_CHAT_FNS = {"generateText", "streamText", "generateObject", "streamObject"}
_EMBED_FNS = {"embed", "embedMany"}

_SOURCE_SIGNALS: tuple[str, ...] = (
    "generateText",
    "streamText",
    "generateObject",
    "streamObject",
    "@ai-sdk",
    "ai/react",
    "embed",
    "embedMany",
)

# Maps a provider wrapper identifier to the SDK name used for pricing.
_PROVIDER_TO_SDK: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google_genai",
    "googleai": "google_genai",
    "vertex": "google_genai",
    "azure": "openai",
    "bedrock": "anthropic",
    "mistral": "litellm",
    "groq": "litellm",
    "xai": "litellm",
    "cohere": "litellm",
    "perplexity": "litellm",
    "togetherai": "litellm",
    "fireworks": "litellm",
    "deepseek": "litellm",
    "cerebras": "litellm",
    "replicate": "litellm",
}


class VercelAiSdkDetector(BaseJsDetector):
    def sdk_name(self) -> str:
        return "vercel_ai_sdk"

    def can_handle(self, root: Node, source: str) -> bool:
        return any(s in source for s in _SOURCE_SIGNALS)

    def detect(
        self,
        root: Node,
        file_path: str,
        source: bytes,
        variables: dict[str, str | int],
    ) -> list[LLMCall]:
        calls: list[LLMCall] = []
        for node in walk_calls(root):
            if node.type != "call_expression":
                continue
            call_fn = _vercel_fn_name(node, source)
            if call_fn is None:
                continue

            args = get_call_arguments(node)
            options = args[0] if args and args[0].type == "object" else None

            model_node = find_object_property(options, source, "model") if options else None
            model = resolve_string(model_node, source, variables) if model_node else None
            model_is_literal = bool(
                model_node and extract_string_literal(model_node, source) is not None
            )

            sdk = _infer_sdk_from_model_node(model_node, source) if model_node else "vercel_ai_sdk"

            if call_fn in _EMBED_FNS:
                call_type = CallType.EMBEDDING
            else:
                call_type = CallType.CHAT_COMPLETION

            max_tokens_node = (
                find_object_property(options, source, "maxOutputTokens") if options else None
            )
            if max_tokens_node is None and options is not None:
                max_tokens_node = find_object_property(options, source, "maxTokens")
            max_tokens = (
                resolve_int(max_tokens_node, source, variables) if max_tokens_node else None
            )

            func = node.child_by_field_name("function")
            raw = node_text(func, source) if func is not None else ""

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.start_point[0] + 1,
                    sdk=sdk,
                    call_type=call_type,
                    model=model,
                    model_is_literal=model_is_literal,
                    max_tokens=max_tokens,
                    estimated_input_tokens=None,
                    estimated_output_tokens=max_tokens,
                    raw_expression=raw,
                )
            )
        return calls


def _vercel_fn_name(call_node: Node, source: bytes) -> str | None:
    """Vercel AI SDK functions are imported and called bare, never as methods.

    Restricting to identifier-shape callees prevents matching client method
    calls like `client.embed(request)` from non-Vercel libraries that happen
    to expose the same function name (e.g., langchain-cohere)."""
    func = call_node.child_by_field_name("function")
    if func is None:
        return None
    if func.type == "identifier":
        name = node_text(func, source)
        if name in _CHAT_FNS or name in _EMBED_FNS:
            return name
    return None


def _infer_sdk_from_model_node(model_node: Node, source: bytes) -> str:
    """Map openai("gpt-4o") -> "openai", anthropic("...") -> "anthropic", etc.

    Falls back to "vercel_ai_sdk" when the wrapper is unknown."""
    model_node = unwrap(model_node)
    if model_node.type != "call_expression":
        return "vercel_ai_sdk"
    func = model_node.child_by_field_name("function")
    if func is None:
        return "vercel_ai_sdk"
    provider_name: str | None = None
    if func.type == "identifier":
        provider_name = node_text(func, source)
    elif func.type == "member_expression":
        path = member_expression_path(func, source)
        if path:
            provider_name = path[0]
    if provider_name and provider_name in _PROVIDER_TO_SDK:
        return _PROVIDER_TO_SDK[provider_name]
    return "vercel_ai_sdk"
