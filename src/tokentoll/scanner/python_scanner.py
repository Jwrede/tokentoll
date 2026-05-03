from __future__ import annotations

import ast
from pathlib import Path

from tokentoll.core.models import LLMCall
from tokentoll.detectors.registry import get_all_detectors

_QUICK_REJECT_PATTERNS = (
    "openai",
    "anthropic",
    "genai",
    "google",
    "litellm",
    "langchain",
    "completions.create",
    "messages.create",
    "embeddings.create",
    "generate_content",
    "completion(",
)


def scan_source(source: str, file_path: str) -> list[LLMCall]:
    """Scan Python source code for LLM API calls."""
    if not any(p in source for p in _QUICK_REJECT_PATTERNS):
        return []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    detectors = [d for d in get_all_detectors() if d.can_handle(tree, source)]
    if not detectors:
        return []

    variables = build_variable_map(tree)

    calls: list[LLMCall] = []
    for detector in detectors:
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


def resolve_kwargs_value(
    call: ast.Call, name: str, variables: dict[str, str | int]
) -> str | int | None:
    """Resolve a value from **kwargs unpacking in a function call.

    When a call has **d, looks up d.name in the variable map.
    """
    for kw in call.keywords:
        if kw.arg is None and isinstance(kw.value, ast.Name):
            dict_name = kw.value.id
            key = f"{dict_name}.{name}"
            if key in variables:
                return variables[key]
    return None


def estimate_tokens_from_string(s: str, model: str | None = None) -> int:
    """Estimate token count. Uses tiktoken if installed, else char/4 heuristic."""
    from tokentoll.tokenizer import estimate_tokens

    return estimate_tokens(s, model)


def estimate_tokens_from_messages(node: ast.expr, model: str | None = None) -> int | None:
    """Estimate input tokens from a messages list literal."""
    from tokentoll.tokenizer import estimate_tokens

    if not isinstance(node, ast.List):
        return None
    parts: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Dict):
            for v in elt.values:
                s = extract_string_literal(v) if v else None
                if s:
                    parts.append(s)
    if not parts:
        return None
    return estimate_tokens(" ".join(parts), model)


def find_imports(tree: ast.Module, package: str) -> list[str]:
    """Find all names imported from a package.

    Returns the imported names (e.g., ['OpenAI', 'AsyncOpenAI'] for
    'from openai import OpenAI, AsyncOpenAI'), or ['openai'] for
    'import openai'.
    """
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package or alias.name.startswith(package + "."):
                    names.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == package or node.module.startswith(package + ".")):
                for alias in node.names:
                    names.append(alias.asname or alias.name)
    return names


def find_imports_by_name(tree: ast.Module, names: set[str]) -> list[str]:
    """Find imports where the resulting local name matches, regardless of source package.

    Catches re-exports like 'from aider.llm import litellm' where the name
    'litellm' is imported from a wrapper, not the original package.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                if local in names:
                    found.append(local)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local = alias.asname or alias.name
                if local in names:
                    found.append(local)
    return found


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
    """Build a map of names to resolved constant values via multi-pass propagation.

    Pass 1: Collect direct constant assignments, function defaults, os.getenv
    Pass 2: Resolve variable-to-variable refs, dict contents, class attrs,
            constructor arg propagation. Iterate until no new resolutions.

    Tracks: simple vars, dict contents (as "dictname.key"), class attrs
    (as "ClassName.attr"), instance attrs (as "varname.attr").
    """
    variables: dict[str, str | int] = {}

    # --- Pass 1: direct constants ---
    _collect_constants(tree, variables)

    # --- Pass 2: propagate until fixed point ---
    for _ in range(5):
        prev_size = len(variables)
        _propagate_variables(tree, variables)
        _propagate_class_attrs(tree, variables)
        _propagate_constructor_args(tree, variables)
        _propagate_dict_contents(tree, variables)
        if len(variables) == prev_size:
            break

    return variables


def _collect_constants(tree: ast.Module, variables: dict[str, str | int]) -> None:
    """Collect direct constant assignments and function defaults."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                val = _extract_constant_value(node.value)
                if val is not None:
                    variables[target.id] = val

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = node.args.defaults
            all_args = node.args.posonlyargs + node.args.args
            if defaults:
                offset = len(all_args) - len(defaults)
                for i, default in enumerate(defaults):
                    idx = offset + i
                    if 0 <= idx < len(all_args):
                        arg_name = all_args[idx].arg
                        val = _extract_constant_value(default)
                        if val is not None:
                            variables[arg_name] = val

            for kwarg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if default is not None:
                    val = _extract_constant_value(default)
                    if val is not None:
                        variables[kwarg.arg] = val


def _propagate_variables(tree: ast.Module, variables: dict[str, str | int]) -> None:
    """Resolve variable-to-variable assignments: x = y where y is known."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id not in variables:
                val = _resolve_expr(node.value, variables)
                if val is not None:
                    variables[target.id] = val


def _propagate_class_attrs(tree: ast.Module, variables: dict[str, str | int]) -> None:
    """Track class-level defaults and self.x = y in __init__."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        class_name = node.name

        for item in ast.walk(node):
            # Class-level: x: str = "value" or x = "value"
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.value:
                    val = _resolve_expr(item.value, variables)
                    if val is not None:
                        variables[f"{class_name}.{item.target.id}"] = val

            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                target = item.targets[0]
                # self.x = y in methods
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    val = _resolve_expr(item.value, variables)
                    if val is not None:
                        variables[f"{class_name}.{target.attr}"] = val


def _propagate_constructor_args(tree: ast.Module, variables: dict[str, str | int]) -> None:
    """Track obj = ClassName(arg) and map args to __init__ params -> self.x."""
    class_defs: dict[str, ast.ClassDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_defs[node.name] = node

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Name) and isinstance(node.value, ast.Call)):
            continue

        func = node.value.func
        class_name = None
        if isinstance(func, ast.Name) and func.id in class_defs:
            class_name = func.id
        elif isinstance(func, ast.Attribute) and func.attr in class_defs:
            class_name = func.attr
        if class_name is None:
            continue

        var_name = target.id
        call = node.value
        cls = class_defs[class_name]

        # Copy class-level attributes to instance: config.model = Config.model
        prefix = f"{class_name}."
        for key, val in list(variables.items()):
            if key.startswith(prefix):
                attr = key[len(prefix) :]
                variables[f"{var_name}.{attr}"] = val

        init_method = None
        for item in cls.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__init__":
                    init_method = item
                    break
        if init_method is None:
            continue

        params = init_method.args.args[1:]  # skip self
        param_map: dict[str, str | int] = {}

        for i, arg in enumerate(call.args):
            if i < len(params):
                val = _resolve_expr(arg, variables)
                if val is not None:
                    param_map[params[i].arg] = val

        for kw in call.keywords:
            if kw.arg:
                val = _resolve_expr(kw.value, variables)
                if val is not None:
                    param_map[kw.arg] = val

        # Walk __init__ body for self.x = param_name
        for item in ast.walk(init_method):
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                t = item.targets[0]
                if (
                    isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id == "self"
                    and isinstance(item.value, ast.Name)
                    and item.value.id in param_map
                ):
                    variables[f"{var_name}.{t.attr}"] = param_map[item.value.id]
                    variables[f"{class_name}.{t.attr}"] = param_map[item.value.id]


def _propagate_dict_contents(tree: ast.Module, variables: dict[str, str | int]) -> None:
    """Track dict literal contents and subscript assignments."""
    for node in ast.walk(tree):
        # d = {"key": value, ...}  or  d = dict(key=value)
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if k and v:
                            key_str = extract_string_literal(k)
                            if key_str:
                                val = _resolve_expr(v, variables)
                                if val is not None:
                                    variables[f"{target.id}.{key_str}"] = val

                elif isinstance(node.value, ast.Call):
                    chain = get_attribute_chain(node.value.func)
                    if chain == ["dict"]:
                        for kw in node.value.keywords:
                            if kw.arg:
                                val = _resolve_expr(kw.value, variables)
                                if val is not None:
                                    variables[f"{target.id}.{kw.arg}"] = val

        # d["key"] = value
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                val = _resolve_expr(node.value, variables)
                if val is not None:
                    variables[f"{target.value.id}.{target.slice.value}"] = val


def _extract_constant_value(node: ast.expr) -> str | int | None:
    """Extract a constant value from an AST expression."""
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


def _resolve_expr(node: ast.expr, variables: dict[str, str | int]) -> str | int | None:
    """Resolve an expression to a constant value using the variable map."""
    val = _extract_constant_value(node)
    if val is not None:
        return val

    # Simple variable: x
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]

    # Attribute access: x.y, self.x, x.y.z
    if isinstance(node, ast.Attribute):
        chain = get_attribute_chain(node)
        dotted = ".".join(chain)
        if dotted in variables:
            return variables[dotted]
        # Try last two parts (e.g., "self.main_model.name" -> "main_model.name")
        if len(chain) >= 2:
            key = f"{chain[-2]}.{chain[-1]}"
            if key in variables:
                return variables[key]

    return None


def resolve_string(
    node: ast.expr | None,
    variables: dict[str, str | int],
    call: ast.Call | None = None,
    kwarg_name: str | None = None,
) -> str | None:
    """Resolve a string value from an AST node, variable lookup, or **kwargs."""
    if node is not None:
        val = _resolve_expr(node, variables)
        if isinstance(val, str):
            return val
    if call is not None and kwarg_name:
        val = resolve_kwargs_value(call, kwarg_name, variables)
        if isinstance(val, str):
            return val
    return None


def resolve_int(
    node: ast.expr | None,
    variables: dict[str, str | int],
    call: ast.Call | None = None,
    kwarg_name: str | None = None,
) -> int | None:
    """Resolve an integer value from an AST node, variable lookup, or **kwargs."""
    if node is not None:
        val = _resolve_expr(node, variables)
        if isinstance(val, int):
            return val
    if call is not None and kwarg_name:
        val = resolve_kwargs_value(call, kwarg_name, variables)
        if isinstance(val, int):
            return val
    return None
