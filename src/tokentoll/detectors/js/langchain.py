"""LangChain.js detector for JavaScript/TypeScript.

Matches:
- new ChatOpenAI({ model: "gpt-4o", ... })
- new ChatAnthropic({ model: "claude-sonnet-4-5", maxTokens: 1024 })
- new ChatGoogleGenerativeAI({ model: "gemini-2.0-flash" })
- new OpenAIEmbeddings({ model: "text-embedding-3-small" })

A new_expression's constructor identifier determines the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.js.base import BaseJsDetector
from tokentoll.scanner.js_resolver import (
    extract_string_literal,
    find_object_property,
    get_call_arguments,
    node_text,
    resolve_int,
    resolve_string,
)
from tokentoll.scanner.js_scanner import walk_calls

if TYPE_CHECKING:
    from tree_sitter import Node


_CONSTRUCTORS: dict[str, tuple[str, CallType]] = {
    "ChatOpenAI": ("openai", CallType.CHAT_COMPLETION),
    "AzureChatOpenAI": ("openai", CallType.CHAT_COMPLETION),
    "OpenAIEmbeddings": ("openai", CallType.EMBEDDING),
    "ChatAnthropic": ("anthropic", CallType.CHAT_COMPLETION),
    "ChatGoogleGenerativeAI": ("google_genai", CallType.CHAT_COMPLETION),
    "ChatVertexAI": ("google_genai", CallType.CHAT_COMPLETION),
    "ChatMistralAI": ("litellm", CallType.CHAT_COMPLETION),
    "ChatGroq": ("litellm", CallType.CHAT_COMPLETION),
    "ChatCohere": ("litellm", CallType.CHAT_COMPLETION),
    "ChatXAI": ("litellm", CallType.CHAT_COMPLETION),
    "ChatTogetherAI": ("litellm", CallType.CHAT_COMPLETION),
}

_SOURCE_SIGNALS: tuple[str, ...] = (
    "@langchain/",
    "langchain",
    "ChatOpenAI",
    "ChatAnthropic",
    "ChatGoogle",
    "ChatMistral",
    "ChatGroq",
    "ChatCohere",
    "OpenAIEmbeddings",
)


class LangChainJsDetector(BaseJsDetector):
    def sdk_name(self) -> str:
        return "langchain"

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
            if node.type != "new_expression":
                continue
            ctor = node.child_by_field_name("constructor")
            if ctor is None or ctor.type != "identifier":
                continue
            ctor_name = node_text(ctor, source)
            if ctor_name not in _CONSTRUCTORS:
                continue
            sdk, call_type = _CONSTRUCTORS[ctor_name]

            args = get_call_arguments(node)
            options = args[0] if args and args[0].type == "object" else None

            model_node = find_object_property(options, source, "model") if options else None
            if model_node is None and options is not None:
                # LangChain.js historically uses modelName for chat models
                model_node = find_object_property(options, source, "modelName")
            model = resolve_string(model_node, source, variables) if model_node else None
            model_is_literal = bool(
                model_node and extract_string_literal(model_node, source) is not None
            )

            max_tokens_node = (
                find_object_property(options, source, "maxTokens") if options else None
            )
            if max_tokens_node is None and options is not None:
                max_tokens_node = find_object_property(options, source, "max_tokens")
            max_tokens = (
                resolve_int(max_tokens_node, source, variables) if max_tokens_node else None
            )

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
                    raw_expression=f"new {ctor_name}",
                )
            )
        return calls
