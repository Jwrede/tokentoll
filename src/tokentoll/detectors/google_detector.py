from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    chain_ends_with,
    estimate_tokens_from_string,
    extract_int_literal,
    extract_string_literal,
    find_imports,
    find_imports_by_name,
    get_attribute_chain,
    get_keyword_value,
    resolve_string,
)

_CALL_PATTERNS: list[tuple[list[str], CallType]] = [
    (["models", "generate_content"], CallType.CHAT_COMPLETION),
    (["models", "generate_content_stream"], CallType.CHAT_COMPLETION),
]


class GoogleDetector(BaseDetector):
    def sdk_name(self) -> str:
        return "google_genai"

    def can_handle(self, tree: ast.Module, source: str) -> bool:
        if find_imports(tree, "google.genai") or find_imports(tree, "google"):
            return True
        return bool(find_imports_by_name(tree, {"genai"}))

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

            max_tokens = _extract_max_output_tokens(node)

            est_input = None
            contents_node = get_keyword_value(node, "contents")
            if contents_node:
                s = extract_string_literal(contents_node)
                if s:
                    est_input = estimate_tokens_from_string(s)

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="google_genai",
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


def _extract_max_output_tokens(call_node: ast.Call) -> int | None:
    """Try to extract max_output_tokens from a config keyword."""
    config_node = get_keyword_value(call_node, "config")
    if config_node is None:
        return None

    if isinstance(config_node, ast.Call):
        val = get_keyword_value(config_node, "max_output_tokens")
        if val:
            return extract_int_literal(val)

    if isinstance(config_node, ast.Dict):
        for k, v in zip(config_node.keys, config_node.values):
            if k and v:
                ks = extract_string_literal(k)
                if ks == "max_output_tokens":
                    return extract_int_literal(v)

    return None
