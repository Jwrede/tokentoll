"""OpenAI Node SDK detector for JavaScript/TypeScript.

Matches:
- client.chat.completions.create({...})    -> CHAT_COMPLETION
- client.responses.create({...})            -> RESPONSES
- client.embeddings.create({...})           -> EMBEDDING

The receiver name (e.g., "client") does not matter; only the trailing
chain is checked. This also catches OpenAI-compatible clients built with
`new OpenAI({ baseURL: "..." })` because the call shape is identical.
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
)
from tokentoll.scanner.js_scanner import walk_calls

if TYPE_CHECKING:
    from tree_sitter import Node


_CALL_PATTERNS: list[tuple[list[str], CallType]] = [
    (["chat", "completions", "create"], CallType.CHAT_COMPLETION),
    (["responses", "create"], CallType.RESPONSES),
    (["embeddings", "create"], CallType.EMBEDDING),
]

_SOURCE_SIGNALS: tuple[str, ...] = (
    "openai",
    "OpenAI",
    "completions.create",
    "responses.create",
    "embeddings.create",
)


class OpenAIJsDetector(BaseJsDetector):
    def sdk_name(self) -> str:
        return "openai"

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
            call_type = _match_call_type(node, source)
            if call_type is None:
                continue

            args = get_call_arguments(node)
            options = args[0] if args and args[0].type == "object" else None

            model_node = find_object_property(options, source, "model") if options else None
            model = resolve_string(model_node, source, variables) if model_node else None
            model_is_literal = bool(
                model_node and extract_string_literal(model_node, source) is not None
            )

            max_tokens_node = (
                find_object_property(options, source, "max_tokens") if options else None
            )
            max_tokens = (
                resolve_int(max_tokens_node, source, variables) if max_tokens_node else None
            )

            func = node.child_by_field_name("function")
            raw = node_text(func, source) if func is not None else ""

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.start_point[0] + 1,
                    sdk="openai",
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


def _match_call_type(call_node: Node, source: bytes) -> CallType | None:
    func = call_node.child_by_field_name("function")
    if func is None or func.type != "member_expression":
        return None
    path = member_expression_path(func, source)
    if path is None:
        return None
    for suffix, ct in _CALL_PATTERNS:
        if len(path) >= len(suffix) and path[-len(suffix) :] == suffix:
            return ct
    return None
