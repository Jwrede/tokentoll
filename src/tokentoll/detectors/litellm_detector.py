from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    estimate_tokens_from_messages,
    extract_string_literal,
    find_imports,
    get_attribute_chain,
    get_keyword_value,
    resolve_int,
    resolve_string,
)

_FUNCTION_MAP: dict[str, CallType] = {
    "completion": CallType.CHAT_COMPLETION,
    "acompletion": CallType.CHAT_COMPLETION,
    "text_completion": CallType.CHAT_COMPLETION,
    "embedding": CallType.EMBEDDING,
    "aembedding": CallType.EMBEDDING,
}


class LiteLLMDetector(BaseDetector):
    def sdk_name(self) -> str:
        return "litellm"

    def can_handle(self, tree: ast.Module, source: str) -> bool:
        return bool(find_imports(tree, "litellm"))

    def detect(
        self,
        tree: ast.Module,
        file_path: str,
        variables: dict[str, str | int] | None = None,
    ) -> list[LLMCall]:
        variables = variables or {}
        imported_names = find_imports(tree, "litellm")

        direct_imports: set[str] = set()
        module_aliases: set[str] = set()
        for name in imported_names:
            if name in _FUNCTION_MAP:
                direct_imports.add(name)
            else:
                module_aliases.add(name)

        calls: list[LLMCall] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_name = None
            call_type = None

            if isinstance(node.func, ast.Name) and node.func.id in direct_imports:
                func_name = node.func.id
                call_type = _FUNCTION_MAP.get(func_name)
            elif isinstance(node.func, ast.Attribute):
                chain = get_attribute_chain(node.func)
                if len(chain) == 2 and chain[0] in module_aliases:
                    func_name = chain[1]
                    call_type = _FUNCTION_MAP.get(func_name)

            if call_type is None:
                continue

            model_node = get_keyword_value(node, "model")
            if model_node is None and node.args:
                model_node = node.args[0]
            model = resolve_string(model_node, variables, call=node, kwarg_name="model")

            max_tokens_node = get_keyword_value(node, "max_tokens")
            max_tokens = resolve_int(max_tokens_node, variables, call=node, kwarg_name="max_tokens")

            est_input = None
            messages_node = get_keyword_value(node, "messages")
            if messages_node:
                est_input = estimate_tokens_from_messages(messages_node)

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="litellm",
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
