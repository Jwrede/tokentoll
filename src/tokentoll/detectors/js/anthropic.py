"""Anthropic Node SDK detector for JavaScript/TypeScript.

Matches:
- client.messages.create({ model, max_tokens, messages, ... })
- client.messages.stream({ model, max_tokens, messages, ... })
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


_CALL_PATTERNS: list[list[str]] = [
    ["messages", "create"],
    ["messages", "stream"],
]

_SOURCE_SIGNALS: tuple[str, ...] = (
    "anthropic",
    "Anthropic",
    "@anthropic-ai/sdk",
    "messages.create",
    "messages.stream",
)


class AnthropicJsDetector(BaseJsDetector):
    def sdk_name(self) -> str:
        return "anthropic"

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
            if not _matches_messages_call(node, source):
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
                    sdk="anthropic",
                    call_type=CallType.CHAT_COMPLETION,
                    model=model,
                    model_is_literal=model_is_literal,
                    max_tokens=max_tokens,
                    estimated_input_tokens=None,
                    estimated_output_tokens=max_tokens,
                    raw_expression=raw,
                )
            )
        return calls


def _matches_messages_call(call_node: Node, source: bytes) -> bool:
    func = call_node.child_by_field_name("function")
    if func is None or func.type != "member_expression":
        return False
    path = member_expression_path(func, source)
    if path is None:
        return False
    for suffix in _CALL_PATTERNS:
        if len(path) >= len(suffix) and path[-len(suffix) :] == suffix:
            return True
    return False
