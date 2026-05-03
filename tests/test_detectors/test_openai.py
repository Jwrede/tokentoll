import ast

from tokentoll.core.models import CallType
from tokentoll.detectors.openai_detector import OpenAIDetector


def _detect(source: str) -> list:
    tree = ast.parse(source)
    d = OpenAIDetector()
    if not d.can_handle(tree, source):
        return []
    return d.detect(tree, "test.py")


def test_chat_completion_basic():
    source = """
from openai import OpenAI
client = OpenAI()
client.chat.completions.create(model="gpt-4o", max_tokens=1000, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].max_tokens == 1000
    assert calls[0].call_type == CallType.CHAT_COMPLETION
    assert calls[0].sdk == "openai"


def test_responses_api():
    source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", input="Hello")
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].call_type == CallType.RESPONSES
    assert calls[0].estimated_input_tokens is not None


def test_async_client():
    source = """
from openai import AsyncOpenAI
client = AsyncOpenAI()
await client.chat.completions.create(model="gpt-4o-mini", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"


def test_embeddings():
    source = """
from openai import OpenAI
client = OpenAI()
client.embeddings.create(model="text-embedding-3-small", input="hello")
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].call_type == CallType.EMBEDDING


def test_variable_model():
    source = """
from openai import OpenAI
client = OpenAI()
model = get_model()
client.chat.completions.create(model=model, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model is None
    assert calls[0].model_is_literal is False


def test_module_level_import():
    source = """
import openai
openai.chat.completions.create(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_no_openai_import():
    source = """
import requests
requests.get("https://example.com")
"""
    tree = ast.parse(source)
    d = OpenAIDetector()
    assert not d.can_handle(tree, source)


def test_multiple_calls():
    source = """
from openai import OpenAI
client = OpenAI()
client.chat.completions.create(model="gpt-4o", messages=[])
client.chat.completions.create(model="gpt-4o-mini", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 2
    models = {c.model for c in calls}
    assert models == {"gpt-4o", "gpt-4o-mini"}
