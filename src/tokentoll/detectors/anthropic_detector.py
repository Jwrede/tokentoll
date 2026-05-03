from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    chain_ends_with,
    estimate_tokens_from_messages,
    estimate_tokens_from_string,
    extract_string_literal,
    find_imports,
    find_imports_by_name,
    get_attribute_chain,
    get_keyword_value,
    resolve_int,
    resolve_string,
)

_CLIENT_CLASSES = {"Anthropic", "AsyncAnthropic"}

_CALL_PATTERNS: list[tuple[list[str], CallType]] = [
    (["messages", "create"], CallType.CHAT_COMPLETION),
    (["messages", "stream"], CallType.CHAT_COMPLETION),
]


class AnthropicDetector(BaseDetector):
    def sdk_name(self) -> str:
        return "anthropic"

    def can_handle(self, tree: ast.Module, source: str) -> bool:
        if find_imports(tree, "anthropic"):
            return True
        if find_imports_by_name(tree, _CLIENT_CLASSES | {"anthropic"}):
            return True
        return ".messages.create" in source

    def detect(
        self,
        tree: ast.Module,
        file_path: str,
        variables: dict[str, str | int] | None = None,
    ) -> list[LLMCall]:
        variables = variables or {}
        calls: list[LLMCall] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            chain = get_attribute_chain(node.func)
            if len(chain) < 2:
                continue

            call_type = None
            for suffix, ct in _CALL_PATTERNS:
                if chain_ends_with(chain, suffix):
                    call_type = ct
                    break
            if call_type is None:
                continue

            model_node = get_keyword_value(node, "model")
            model = resolve_string(model_node, variables, call=node, kwarg_name="model")

            max_tokens_node = get_keyword_value(node, "max_tokens")
            max_tokens = resolve_int(max_tokens_node, variables, call=node, kwarg_name="max_tokens")

            est_input = None
            messages_node = get_keyword_value(node, "messages")
            if messages_node:
                est_input = estimate_tokens_from_messages(messages_node, model)

            system_node = get_keyword_value(node, "system")
            if system_node:
                s = extract_string_literal(system_node)
                if s:
                    system_tokens = estimate_tokens_from_string(s, model)
                    est_input = (est_input or 0) + system_tokens

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="anthropic",
                    call_type=call_type,
                    model=model,
                    model_is_literal=(
                        model_node is not None and extract_string_literal(model_node) is not None
                    ),
                    max_tokens=max_tokens,
                    estimated_input_tokens=est_input,
                    estimated_output_tokens=max_tokens,
                    raw_expression=ast.unparse(node.func),
                )
            )

        return calls
