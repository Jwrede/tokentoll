"""Value resolution for tree-sitter JavaScript/TypeScript AST nodes.

Handles:
- Direct string/template literals.
- Identifier lookup against a same-file variable map.
- Member expression lookup (obj.field).
- process.env.X || "fallback" and process.env.X ?? "fallback".
- Provider wrappers used by the Vercel AI SDK: openai("gpt-4o"),
  anthropic("..."), google("..."), and similar. Also handles the
  .chat()/.embedding() variant: openai.chat("gpt-4o").

The variable map keys are dotted: simple identifiers like "MODEL",
object property paths like "config.model", function defaults like
"model" (function parameter name).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node


_PROVIDER_WRAPPERS: frozenset[str] = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "googleai",
        "vertex",
        "azure",
        "bedrock",
        "mistral",
        "groq",
        "xai",
        "cohere",
        "perplexity",
        "togetherai",
        "fireworks",
        "deepseek",
        "cerebras",
        "replicate",
    }
)


def node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


# TypeScript node types that wrap an inner expression without changing its
# runtime value. We unwrap these before extracting or resolving so that
# `MODEL as Foo`, `MODEL!`, `(MODEL)`, `MODEL satisfies Foo`, and the legacy
# `<Foo>MODEL` all behave the same as `MODEL`.
_WRAPPER_TYPES: frozenset[str] = frozenset(
    {
        "as_expression",
        "satisfies_expression",
        "non_null_expression",
        "parenthesized_expression",
        "type_assertion",
    }
)


def unwrap(node: Node) -> Node:
    """Strip TypeScript type wrappers and parentheses from an expression node."""
    while node.type in _WRAPPER_TYPES:
        # type_assertion is `<T>value`: type comes first, then value.
        # All other wrappers have value first.
        if node.type == "type_assertion":
            value = None
            for c in node.children:
                if c.is_named and c.type != "type_arguments":
                    value = c
                    break
            if value is None:
                return node
            node = value
        else:
            inner = None
            for c in node.children:
                if c.is_named:
                    inner = c
                    break
            if inner is None:
                return node
            node = inner
    return node


def extract_string_literal(node: Node, source: bytes) -> str | None:
    """Return the string value if node is a literal string or template
    string without interpolation. Returns None otherwise."""
    node = unwrap(node)
    if node.type == "string":
        parts: list[str] = []
        for c in node.children:
            if c.type == "string_fragment":
                parts.append(node_text(c, source))
            elif c.type == "escape_sequence":
                parts.append(_decode_escape(node_text(c, source)))
        return "".join(parts)
    if node.type == "template_string":
        if any(c.type == "template_substitution" for c in node.children):
            return None
        parts = []
        for c in node.children:
            if c.type == "string_fragment":
                parts.append(node_text(c, source))
            elif c.type == "escape_sequence":
                parts.append(_decode_escape(node_text(c, source)))
        return "".join(parts)
    return None


def extract_int_literal(node: Node, source: bytes) -> int | None:
    node = unwrap(node)
    if node.type != "number":
        return None
    text = node_text(node, source)
    try:
        return int(text)
    except ValueError:
        try:
            f = float(text)
            if f.is_integer():
                return int(f)
        except ValueError:
            pass
    return None


def member_expression_path(node: Node, source: bytes) -> list[str] | None:
    """Build ['a', 'b', 'c'] from a member_expression node a.b.c.

    Returns None if any segment is computed (e.g., a[b])."""
    parts: list[str] = []
    current = node
    while current.type == "member_expression":
        prop = current.child_by_field_name("property")
        if prop is None or prop.type != "property_identifier":
            return None
        parts.append(node_text(prop, source))
        obj = current.child_by_field_name("object")
        if obj is None:
            return None
        current = obj
    if current.type == "identifier":
        parts.append(node_text(current, source))
    elif current.type == "this":
        parts.append("this")
    elif current.type == "super":
        parts.append("super")
    else:
        return None
    parts.reverse()
    return parts


def find_object_property(object_node: Node, source: bytes, key: str) -> Node | None:
    """In an `object` node, find the value node for property `key`.

    Returns the VALUE node, not the pair. Handles both
    `{ key: value }` (pair) and `{ key }` (shorthand_property_identifier)."""
    if object_node.type != "object":
        return None
    for child in object_node.children:
        if child.type == "pair":
            k = child.child_by_field_name("key")
            v = child.child_by_field_name("value")
            if k is None or v is None:
                continue
            if k.type in ("property_identifier", "identifier"):
                if node_text(k, source) == key:
                    return v
            elif k.type == "string":
                if extract_string_literal(k, source) == key:
                    return v
        elif child.type == "shorthand_property_identifier":
            if node_text(child, source) == key:
                return child
    return None


def get_call_arguments(call_node: Node) -> list[Node]:
    """Return positional arg value nodes of a call_expression or new_expression."""
    args = call_node.child_by_field_name("arguments")
    if args is None:
        return []
    result = []
    for c in args.children:
        if c.type in ("(", ",", ")"):
            continue
        result.append(c)
    return result


def resolve_string(
    node: Node | None,
    source: bytes,
    variables: dict[str, str | int],
) -> str | None:
    """Resolve a node to a string with fallback strategies."""
    if node is None:
        return None
    node = unwrap(node)

    direct = extract_string_literal(node, source)
    if direct is not None:
        return direct

    if node.type == "identifier":
        name = node_text(node, source)
        val = variables.get(name)
        if isinstance(val, str):
            return val
        return None

    if node.type == "member_expression":
        path = member_expression_path(node, source)
        if path is not None:
            dotted = ".".join(path)
            val = variables.get(dotted)
            if isinstance(val, str):
                return val
            if len(path) >= 2:
                tail = ".".join(path[-2:])
                val = variables.get(tail)
                if isinstance(val, str):
                    return val
        return None

    if node.type == "binary_expression":
        op_child = None
        for c in node.children:
            if c.type in ("||", "??"):
                op_child = c
                break
        if op_child is not None:
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if right is not None:
                if left is not None and _is_process_env_or_dynamic(left, source):
                    return resolve_string(right, source, variables)
        return None

    if node.type == "call_expression":
        return _resolve_provider_wrapper(node, source, variables)

    return None


def resolve_int(
    node: Node | None,
    source: bytes,
    variables: dict[str, str | int],
) -> int | None:
    if node is None:
        return None
    node = unwrap(node)

    direct = extract_int_literal(node, source)
    if direct is not None:
        return direct

    if node.type == "identifier":
        name = node_text(node, source)
        val = variables.get(name)
        if isinstance(val, int):
            return val
        return None

    if node.type == "member_expression":
        path = member_expression_path(node, source)
        if path is not None:
            dotted = ".".join(path)
            val = variables.get(dotted)
            if isinstance(val, int):
                return val
        return None

    if node.type == "binary_expression":
        op_child = None
        for c in node.children:
            if c.type in ("||", "??"):
                op_child = c
                break
        if op_child is not None:
            right = node.child_by_field_name("right")
            if right is not None:
                return resolve_int(right, source, variables)

    return None


def _resolve_provider_wrapper(
    call_node: Node, source: bytes, variables: dict[str, str | int]
) -> str | None:
    """openai("gpt-4o") or openai.chat("gpt-4o") -> "gpt-4o"."""
    func = call_node.child_by_field_name("function")
    if func is None:
        return None

    provider_name: str | None = None
    if func.type == "identifier":
        provider_name = node_text(func, source)
    elif func.type == "member_expression":
        path = member_expression_path(func, source)
        if path and len(path) >= 1:
            provider_name = path[0]

    if provider_name is None or provider_name not in _PROVIDER_WRAPPERS:
        return None

    args = get_call_arguments(call_node)
    if not args:
        return None
    return resolve_string(args[0], source, variables)


def _is_process_env_or_dynamic(node: Node, source: bytes) -> bool:
    """Heuristic: treat the left operand of ||/?? as 'dynamic' if it is
    process.env.X, an identifier, or any member_expression. Lets us treat
    the right operand as the meaningful fallback model."""
    if node.type == "identifier":
        return True
    if node.type == "member_expression":
        path = member_expression_path(node, source)
        if path is None:
            return True
        return True
    return False


def _decode_escape(seq: str) -> str:
    try:
        return bytes(seq, "utf-8").decode("unicode_escape")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return seq
