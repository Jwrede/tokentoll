import ast

from tokentoll.core.models import CallType
from tokentoll.detectors.litellm_detector import LiteLLMDetector


def _detect(source: str) -> list:
    tree = ast.parse(source)
    d = LiteLLMDetector()
    if not d.can_handle(tree, source):
        return []
    return d.detect(tree, "test.py")


def test_module_completion():
    source = """
import litellm
litellm.completion(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].sdk == "litellm"
    assert calls[0].call_type == CallType.CHAT_COMPLETION


def test_direct_import():
    source = """
from litellm import completion
completion(model="gpt-4o-mini", max_tokens=500, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"
    assert calls[0].max_tokens == 500


def test_acompletion():
    source = """
from litellm import acompletion
await acompletion(model="claude-sonnet-4-20250514", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1


def test_embedding():
    source = """
import litellm
litellm.embedding(model="text-embedding-3-small", input="hello")
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].call_type == CallType.EMBEDDING


def test_positional_model():
    source = """
from litellm import completion
completion("openai/gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "openai/gpt-4o"


def test_reexported_module():
    source = """
from myapp.llm import litellm
litellm.completion(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
