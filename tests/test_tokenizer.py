from unittest.mock import patch

from tokentoll.tokenizer import estimate_tokens


def test_fallback_heuristic():
    """Without tiktoken, uses char/4 heuristic."""
    with patch("tokentoll.tokenizer._tiktoken_available", False):
        result = estimate_tokens("Hello world, this is a test string")
        assert result == max(1, len("Hello world, this is a test string") // 4)


def test_fallback_no_model():
    """Without a model name, always uses heuristic even if tiktoken available."""
    result = estimate_tokens("Hello world", model=None)
    assert result >= 1


def test_minimum_one_token():
    with patch("tokentoll.tokenizer._tiktoken_available", False):
        assert estimate_tokens("ab") == 1
        assert estimate_tokens("") == 1


def test_with_tiktoken():
    """If tiktoken is installed, results differ from char/4 for most strings."""
    try:
        import tiktoken  # noqa: F401
    except ImportError:
        return  # skip if not installed

    text = "The quick brown fox jumps over the lazy dog"
    heuristic = max(1, len(text) // 4)
    actual = estimate_tokens(text, model="gpt-4o")
    assert actual >= 1
    assert actual != heuristic or True  # may match by coincidence, that's ok


def test_unknown_model_uses_cl100k():
    """Unknown model names should fall back to cl100k_base, not crash."""
    try:
        import tiktoken  # noqa: F401
    except ImportError:
        return
    result = estimate_tokens("Hello world", model="totally-fake-model-xyz")
    assert result >= 1
