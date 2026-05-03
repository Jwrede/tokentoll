from __future__ import annotations

_tiktoken_available: bool | None = None
_encoder_cache: dict[str, object] = {}


def _check_tiktoken() -> bool:
    global _tiktoken_available
    if _tiktoken_available is None:
        try:
            import tiktoken  # noqa: F401

            _tiktoken_available = True
        except ImportError:
            _tiktoken_available = False
    return _tiktoken_available


def estimate_tokens(text: str, model: str | None = None) -> int:
    """Estimate token count. Uses tiktoken if installed, else char/4 heuristic."""
    if _check_tiktoken() and model:
        return _count_with_tiktoken(text, model)
    return max(1, len(text) // 4)


def _count_with_tiktoken(text: str, model: str) -> int:
    try:
        enc = _get_encoder(model)
        return max(1, len(enc.encode(text)))
    except Exception:
        return max(1, len(text) // 4)


def _get_encoder(model: str) -> object:
    import tiktoken

    if model not in _encoder_cache:
        try:
            _encoder_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            _encoder_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoder_cache[model]
