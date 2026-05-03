from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    chain_ends_with,
    estimate_tokens_from_messages,
    extract_int_literal,
    extract_string_literal,
    find_assigned_names,
    find_imports,
    get_attribute_chain,
    get_keyword_value,
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
        return bool(find_imports(tree, "anthropic"))

    def detect(self, tree: ast.Module, file_path: str) -> list[LLMCall]:
        imported_names = find_imports(tree, "anthropic")
        client_vars = find_assigned_names(tree, _CLIENT_CLASSES)

        module_aliases: set[str] = set()
        for name in imported_names:
            if name == "anthropic" or name not in _CLIENT_CLASSES:
                module_aliases.add(name)

        valid_bases = client_vars | module_aliases | _CLIENT_CLASSES
        calls: list[LLMCall] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            chain = get_attribute_chain(node.func)
            if len(chain) < 2:
                continue
            if chain[0] not in valid_bases:
                continue

            call_type = None
            for suffix, ct in _CALL_PATTERNS:
                if chain_ends_with(chain, suffix):
                    call_type = ct
                    break
            if call_type is None:
                continue

            model_node = get_keyword_value(node, "model")
            model = extract_string_literal(model_node) if model_node else None

            max_tokens_node = get_keyword_value(node, "max_tokens")
            max_tokens = extract_int_literal(max_tokens_node) if max_tokens_node else None

            est_input = None
            messages_node = get_keyword_value(node, "messages")
            if messages_node:
                est_input = estimate_tokens_from_messages(messages_node)

            system_node = get_keyword_value(node, "system")
            if system_node:
                s = extract_string_literal(system_node)
                if s:
                    system_tokens = max(1, len(s) // 4)
                    est_input = (est_input or 0) + system_tokens

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="anthropic",
                    call_type=call_type,
                    model=model,
                    model_is_literal=model is not None,
                    max_tokens=max_tokens,
                    estimated_input_tokens=est_input,
                    estimated_output_tokens=max_tokens,
                    raw_expression=ast.unparse(node.func),
                )
            )

        return calls
