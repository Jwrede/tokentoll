"""Tree-sitter based scanner for JavaScript and TypeScript files.

Public API:
- scan_source_js(source, file_path) -> list[LLMCall]
- parse(source: bytes, file_path: str) -> Tree | None
- build_variable_map(root, source) -> dict[str, str | int]
- walk_calls(root) -> iterator over call_expression and new_expression nodes

The variable map is a same-file constant propagation pass: it collects
top-level `const X = "..."`, `let X = ...`, function default params,
and object-literal initializers, so detectors can resolve `model: MODEL`
or `model: cfg.model` against literal values declared elsewhere in the
same file. There is no cross-file resolution in v0.8.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from tokentoll.core.models import LLMCall
from tokentoll.scanner.js_resolver import (
    extract_int_literal,
    extract_string_literal,
    member_expression_path,
    node_text,
    unwrap,
)

if TYPE_CHECKING:
    from tree_sitter import Node, Tree


_QUICK_REJECT_PATTERNS = (
    "openai",
    "anthropic",
    "OpenAI",
    "Anthropic",
    "ChatOpenAI",
    "ChatAnthropic",
    "ChatGoogle",
    "generateText",
    "streamText",
    "completions.create",
    "messages.create",
    "responses.create",
    "@ai-sdk",
    "langchain",
)

_LANGUAGES: dict[str, object] = {}


def _get_language(ext: str):
    """Lazy-load and cache tree-sitter Language objects."""
    if ext in _LANGUAGES:
        return _LANGUAGES[ext]

    from tree_sitter import Language

    if ext == ".tsx":
        import tree_sitter_typescript as ts_ts

        lang = Language(ts_ts.language_tsx())
    elif ext == ".ts":
        import tree_sitter_typescript as ts_ts

        lang = Language(ts_ts.language_typescript())
    elif ext in (".js", ".jsx"):
        import tree_sitter_javascript as ts_js

        lang = Language(ts_js.language())
    else:
        raise ValueError(f"Unsupported extension: {ext}")

    _LANGUAGES[ext] = lang
    return lang


def parse(source: bytes, file_path: str) -> Tree | None:
    from tree_sitter import Parser

    ext = Path(file_path).suffix
    try:
        lang = _get_language(ext)
    except ValueError:
        return None
    parser = Parser(lang)
    try:
        return parser.parse(source)
    except Exception:
        return None


def scan_source_js(source: str, file_path: str) -> list[LLMCall]:
    if not any(p in source for p in _QUICK_REJECT_PATTERNS):
        return []

    source_bytes = source.encode("utf-8")
    tree = parse(source_bytes, file_path)
    if tree is None:
        return []

    root = tree.root_node
    variables = build_variable_map(root, source_bytes)

    from tokentoll.detectors.js.registry import get_all_js_detectors

    calls: list[LLMCall] = []
    for detector in get_all_js_detectors():
        if not detector.can_handle(root, source):
            continue
        calls.extend(detector.detect(root, file_path, source_bytes, variables))
    return calls


def walk_calls(root: Node) -> Iterator[Node]:
    """Yield every call_expression and new_expression node under root."""
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        if node.type in ("call_expression", "new_expression"):
            yield node
        for c in reversed(node.children):
            stack.append(c)


def walk(root: Node) -> Iterator[Node]:
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        yield node
        for c in reversed(node.children):
            stack.append(c)


def build_variable_map(root: Node, source: bytes) -> dict[str, str | int]:
    """Same-file constant propagation. Returns dotted-key map."""
    variables: dict[str, str | int] = {}

    for node in walk(root):
        if node.type == "variable_declarator":
            _collect_declarator(node, source, variables)
        elif node.type in ("formal_parameters",):
            _collect_param_defaults(node, source, variables)

    # Second pass: identifier-to-identifier (let X = Y where Y is known).
    # Run a couple of times for chains.
    for _ in range(3):
        prev_size = len(variables)
        for node in walk(root):
            if node.type != "variable_declarator":
                continue
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if name_node is None or value_node is None:
                continue
            if name_node.type != "identifier":
                continue
            name = node_text(name_node, source)
            if name in variables:
                continue
            if value_node.type == "identifier":
                ref = node_text(value_node, source)
                if ref in variables:
                    variables[name] = variables[ref]
        if len(variables) == prev_size:
            break

    return variables


def _collect_declarator(node: Node, source: bytes, variables: dict[str, str | int]) -> None:
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is None or value_node is None:
        return

    if name_node.type == "identifier":
        name = node_text(name_node, source)
        value_node = unwrap(value_node)
        # Literal string / number
        s = extract_string_literal(value_node, source)
        if s is not None:
            variables[name] = s
            return
        i = extract_int_literal(value_node, source)
        if i is not None:
            variables[name] = i
            return
        # Object literal: { key: "value", nested: 42 }
        if value_node.type == "object":
            _collect_object_literal(name, value_node, source, variables)
            return
        # process.env.X || "fallback"  -> bind name to "fallback"
        if value_node.type == "binary_expression":
            for c in value_node.children:
                if c.type in ("||", "??"):
                    right = value_node.child_by_field_name("right")
                    if right is not None:
                        s2 = extract_string_literal(right, source)
                        if s2 is not None:
                            variables[name] = s2
                            return
                        i2 = extract_int_literal(right, source)
                        if i2 is not None:
                            variables[name] = i2
                            return
                    break


def _collect_object_literal(
    prefix: str, obj_node: Node, source: bytes, variables: dict[str, str | int]
) -> None:
    for child in obj_node.children:
        if child.type != "pair":
            continue
        k = child.child_by_field_name("key")
        v = child.child_by_field_name("value")
        if k is None or v is None:
            continue
        if k.type in ("property_identifier", "identifier"):
            key_name = node_text(k, source)
        elif k.type == "string":
            key_name = extract_string_literal(k, source) or ""
        else:
            continue
        if not key_name:
            continue
        full = f"{prefix}.{key_name}"
        s = extract_string_literal(v, source)
        if s is not None:
            variables[full] = s
            continue
        i = extract_int_literal(v, source)
        if i is not None:
            variables[full] = i
            continue
        if v.type == "member_expression":
            path = member_expression_path(v, source)
            if path:
                ref = ".".join(path)
                if ref in variables:
                    variables[full] = variables[ref]


def _collect_param_defaults(
    params_node: Node, source: bytes, variables: dict[str, str | int]
) -> None:
    """Collect function default parameter values across both grammars.

    TS grammar emits `required_parameter` / `optional_parameter` with
    fields `pattern` (the name) and `value` (the default). JS grammar
    emits `assignment_pattern` with `left` and `right` fields.
    """
    for child in params_node.children:
        if child.type in ("required_parameter", "optional_parameter"):
            name_node = child.child_by_field_name("pattern")
            value_node = child.child_by_field_name("value")
            _bind_default(name_node, value_node, source, variables)
        elif child.type == "assignment_pattern":
            left = child.child_by_field_name("left")
            right = child.child_by_field_name("right")
            _bind_default(left, right, source, variables)


def _bind_default(
    name_node: Node | None,
    value_node: Node | None,
    source: bytes,
    variables: dict[str, str | int],
) -> None:
    if name_node is None or value_node is None or name_node.type != "identifier":
        return
    name = node_text(name_node, source)
    if name in variables:
        return
    s = extract_string_literal(value_node, source)
    if s is not None:
        variables[name] = s
        return
    i = extract_int_literal(value_node, source)
    if i is not None:
        variables[name] = i
