import ast

from tokentoll.core.models import CallType
from tokentoll.detectors.google_detector import GoogleDetector


def _detect(source: str) -> list:
    tree = ast.parse(source)
    d = GoogleDetector()
    if not d.can_handle(tree, source):
        return []
    return d.detect(tree, "test.py")


def test_generate_content():
    source = """
from google import genai
client = genai.Client()
client.models.generate_content(model="gemini-2.5-flash", contents="Hello")
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gemini-2.5-flash"
    assert calls[0].sdk == "google_genai"
    assert calls[0].call_type == CallType.CHAT_COMPLETION


def test_with_config_dict():
    source = """
from google import genai
client = genai.Client()
client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello",
    config={"max_output_tokens": 2048},
)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].max_tokens == 2048
