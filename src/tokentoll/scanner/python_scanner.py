from __future__ import annotations

import ast
from pathlib import Path

from tokentoll.core.models import LLMCall
from tokentoll.detectors.registry import get_all_detectors


def scan_source(source: str, file_path: str) -> list[LLMCall]:
    """Scan Python source code for LLM API calls."""
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    variables = build_variable_map(tree)

    calls: list[LLMCall] = []
    for detector in get_all_detectors():
        if detector.can_handle(tree, source):
            calls.extend(detector.detect(tree, file_path, variables))
    return calls


def scan_file(path: Path) -> list[LLMCall]:
    """Scan a single Python file for LLM API calls."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_source(source, str(path))


def scan_paths(paths: list[str]) -> list[LLMCall]:
    """Scan one or more paths (files or directories) for LLM API calls."""
    all_calls: list[LLMCall] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix == ".py":
            all_calls.extend(scan_file(path))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                all_calls.extend(scan_file(py_file))
    return all_calls


# --- AST helper utilities ---


def get_attribute_chain(node: ast.expr) -> list[str]:
    """Build ['a', 'b', 'c'] from a.b.c AST node."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    return parts


def chain_ends_with(chain: list[str], suffix: list[str]) -> bool:
    """Check if attribute chain ends with the given suffix."""
    if len(chain) < len(suffix):
        return False
    return chain[-len(suffix) :] == suffix


def extract_string_literal(node: ast.expr) -> str | None:
    """Extract string value if node is a string constant."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_int_literal(node: ast.expr) -> int | None:
    """Extract integer value if node is an integer constant."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def get_keyword_value(call: ast.Call, name: str) -> ast.expr | None:
    """Get the value node for a keyword argument by name."""
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def estimate_tokens_from_string(s: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return max(1, len(s) // 4)


def estimate_tokens_from_messages(node: ast.expr) -> int | None:
    """Estimate input tokens from a messages list literal."""
    if not isinstance(node, ast.List):
        return None
    total_chars = 0
    for elt in node.elts:
        if isinstance(elt, ast.Dict):
            for v in elt.values:
                s = extract_string_literal(v) if v else None
                if s:
                    total_chars += len(s)
    if total_chars == 0:
        return None
    return max(1, total_chars // 4)


def find_imports(tree: ast.Module, package: str) -> list[str]:
    """Find all names imported from a package.

    Returns the imported names (e.g., ['OpenAI', 'AsyncOpenAI'] for
    'from openai import OpenAI, AsyncOpenAI'), or ['openai'] for
    'import openai'.
    """
    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package or alias.name.startswith(package + "."):
                    names.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == package or node.module.startswith(package + ".")):
                for alias in node.names:
                    names.append(alias.asname or alias.name)
    return names


def find_assigned_names(tree: ast.Module, class_names: set[str]) -> set[str]:
    """Find variable names assigned from constructor calls.

    E.g., for class_names={'OpenAI', 'AsyncOpenAI'}, finds 'client' in:
        client = OpenAI()
    """
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                func = node.value.func
                func_name = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name in class_names:
                    result.add(target.id)
    return result


def build_variable_map(tree: ast.Module) -> dict[str, str | int]:
    """Build a map of variable names to their constant values.

    Tracks simple assignments like:
        MODEL = "gpt-4o"
        MAX_TOKENS = 1000
        model = os.getenv("MODEL", "gpt-4o")  -> extracts fallback "gpt-4o"
        model = os.environ.get("MODEL", "gpt-4o")  -> extracts fallback "gpt-4o"

    Also tracks function default arguments:
        def call_llm(model="gpt-4o", ...):  -> model = "gpt-4o"

    Later assignments overwrite earlier ones (last-write wins).
    """
    variables: dict[str, str | int] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                val = _extract_constant_value(node.value)
                if val is not None:
                    variables[target.id] = val

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = node.args.defaults
            args = node.args.args
            if defaults:
                offset = len(args) - len(defaults)
                for i, default in enumerate(defaults):
                    arg_name = args[offset + i].arg
                    val = _extract_constant_value(default)
                    if val is not None:
                        variables[arg_name] = val

            for kw_default in node.args.kw_defaults:
                if kw_default is not None:
                    val = _extract_constant_value(kw_default)
                    if val is not None:
                        pass

            for kwarg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if default is not None:
                    val = _extract_constant_value(default)
                    if val is not None:
                        variables[kwarg.arg] = val

    return variables


def _extract_constant_value(node: ast.expr) -> str | int | None:
    """Extract a constant value from an AST expression.

    Handles:
    - String/int literals: "gpt-4o", 1000
    - os.getenv("KEY", "default") -> extracts "default"
    - os.environ.get("KEY", "default") -> extracts "default"
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int)):
            return node.value
        return None

    if isinstance(node, ast.Call):
        chain = get_attribute_chain(node.func)
        chain_str = ".".join(chain)
        if chain_str in ("os.getenv", "os.environ.get"):
            if len(node.args) >= 2:
                return _extract_constant_value(node.args[1])
            default_kw = get_keyword_value(node, "default")
            if default_kw:
                return _extract_constant_value(default_kw)

    return None


def resolve_string(node: ast.expr | None, variables: dict[str, str | int]) -> str | None:
    """Resolve a string value from an AST node, falling back to variable lookup."""
    if node is None:
        return None
    lit = extract_string_literal(node)
    if lit is not None:
        return lit
    if isinstance(node, ast.Name) and node.id in variables:
        val = variables[node.id]
        if isinstance(val, str):
            return val
    return None


def resolve_int(node: ast.expr | None, variables: dict[str, str | int]) -> int | None:
    """Resolve an integer value from an AST node, falling back to variable lookup."""
    if node is None:
        return None
    lit = extract_int_literal(node)
    if lit is not None:
        return lit
    if isinstance(node, ast.Name) and node.id in variables:
        val = variables[node.id]
        if isinstance(val, int):
            return val
    return None
