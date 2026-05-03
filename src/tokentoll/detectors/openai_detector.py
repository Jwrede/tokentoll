from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    chain_ends_with,
    estimate_tokens_from_messages,
    estimate_tokens_from_string,
    extract_int_literal,
    extract_string_literal,
    find_assigned_names,
    find_imports,
    get_attribute_chain,
    get_keyword_value,
)

_CLIENT_CLASSES = {"OpenAI", "AsyncOpenAI"}

_CALL_PATTERNS: list[tuple[list[str], CallType]] = [
    (["chat", "completions", "create"], CallType.CHAT_COMPLETION),
    (["responses", "create"], CallType.RESPONSES),
    (["embeddings", "create"], CallType.EMBEDDING),
    (["images", "generate"], CallType.IMAGE_GENERATION),
]


class OpenAIDetector(BaseDetector):
    def sdk_name(self) -> str:
        return "openai"

    def can_handle(self, tree: ast.Module, source: str) -> bool:
        return bool(find_imports(tree, "openai"))

    def detect(self, tree: ast.Module, file_path: str) -> list[LLMCall]:
        imported_names = find_imports(tree, "openai")
        client_vars = find_assigned_names(tree, _CLIENT_CLASSES)

        module_aliases: set[str] = set()
        for name in imported_names:
            if name == "openai" or name not in _CLIENT_CLASSES:
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
            model_is_literal = model is not None

            max_tokens_node = get_keyword_value(node, "max_tokens")
            max_tokens = extract_int_literal(max_tokens_node) if max_tokens_node else None

            est_input = None
            est_output = max_tokens

            if call_type == CallType.CHAT_COMPLETION:
                messages_node = get_keyword_value(node, "messages")
                if messages_node:
                    est_input = estimate_tokens_from_messages(messages_node)
            elif call_type == CallType.RESPONSES:
                input_node = get_keyword_value(node, "input")
                if input_node:
                    s = extract_string_literal(input_node)
                    if s:
                        est_input = estimate_tokens_from_string(s)

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="openai",
                    call_type=call_type,
                    model=model,
                    model_is_literal=model_is_literal,
                    max_tokens=max_tokens,
                    estimated_input_tokens=est_input,
                    estimated_output_tokens=est_output,
                    raw_expression=ast.unparse(node.func),
                )
            )

        return calls
