from __future__ import annotations

import ast

from tokentoll.core.models import CallType, LLMCall
from tokentoll.detectors.base import BaseDetector
from tokentoll.scanner.python_scanner import (
    extract_string_literal,
    find_imports,
    get_keyword_value,
    resolve_int,
    resolve_string,
)

_LANGCHAIN_PACKAGES = [
    "langchain_openai",
    "langchain_anthropic",
    "langchain_google_genai",
    "langchain_community",
    "langchain.chat_models",
]

_CHAT_MODEL_CLASSES = {
    "ChatOpenAI",
    "AzureChatOpenAI",
    "ChatAnthropic",
    "ChatGoogleGenerativeAI",
    "ChatLiteLLM",
}

_INIT_FUNCTIONS = {
    "init_chat_model",
}


class LangChainDetector(BaseDetector):
    def sdk_name(self) -> str:
        return "langchain"

    def can_handle(self, tree: ast.Module, source: str) -> bool:
        for pkg in _LANGCHAIN_PACKAGES:
            if find_imports(tree, pkg):
                return True
        return False

    def detect(
        self,
        tree: ast.Module,
        file_path: str,
        variables: dict[str, str | int] | None = None,
    ) -> list[LLMCall]:
        variables = variables or {}
        imported_classes: set[str] = set()
        imported_functions: set[str] = set()

        for pkg in _LANGCHAIN_PACKAGES:
            for name in find_imports(tree, pkg):
                if name in _CHAT_MODEL_CLASSES:
                    imported_classes.add(name)
                elif name in _INIT_FUNCTIONS:
                    imported_functions.add(name)

        calls: list[LLMCall] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name is None:
                continue

            is_constructor = func_name in imported_classes
            is_init_func = func_name in imported_functions

            if not is_constructor and not is_init_func:
                continue

            model_node = get_keyword_value(node, "model") or get_keyword_value(node, "model_name")
            if model_node is None and node.args:
                model_node = node.args[0]
            model = resolve_string(model_node, variables)

            max_tokens_node = get_keyword_value(node, "max_tokens") or get_keyword_value(
                node, "max_output_tokens"
            )
            max_tokens = resolve_int(max_tokens_node, variables)

            calls.append(
                LLMCall(
                    file_path=file_path,
                    line_number=node.lineno,
                    sdk="langchain",
                    call_type=CallType.CHAT_COMPLETION,
                    model=model,
                    model_is_literal=(
                        model_node is not None and extract_string_literal(model_node) is not None
                    ),
                    max_tokens=max_tokens,
                    estimated_input_tokens=None,
                    estimated_output_tokens=max_tokens,
                    raw_expression=ast.unparse(node.func),
                )
            )

        return calls
