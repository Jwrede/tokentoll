import ast

from tokentoll.core.models import CallType
from tokentoll.detectors.anthropic_detector import AnthropicDetector


def _detect(source: str) -> list:
    tree = ast.parse(source)
    d = AnthropicDetector()
    if not d.can_handle(tree, source):
        return []
    return d.detect(tree, "test.py")


def test_messages_create():
    source = """
from anthropic import Anthropic
client = Anthropic()
client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1024, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "claude-sonnet-4-20250514"
    assert calls[0].max_tokens == 1024
    assert calls[0].sdk == "anthropic"
    assert calls[0].call_type == CallType.CHAT_COMPLETION


def test_messages_stream():
    source = """
from anthropic import Anthropic
client = Anthropic()
client.messages.stream(model="claude-sonnet-4-20250514", max_tokens=512, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1


def test_with_system_prompt():
    source = """
from anthropic import Anthropic
client = Anthropic()
client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are a helpful assistant.",
    messages=[],
)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].estimated_input_tokens is not None
    assert calls[0].estimated_input_tokens > 0


def test_async_client():
    source = """
from anthropic import AsyncAnthropic
client = AsyncAnthropic()
await client.messages.create(model="claude-sonnet-4-20250514", max_tokens=256, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1


def test_constructor_without_visible_import():
    source = """
client = Anthropic(api_key="x")
client.messages.create(model="claude-sonnet-4-20250514", max_tokens=512, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "claude-sonnet-4-20250514"


def test_compatible_client_without_anthropic_import_not_detected():
    # Some SDKs expose an Anthropic-compatible .messages.create() method
    # without being the Anthropic client. Don't misidentify them.
    source = """
from someotherclient import OtherClient
client = OtherClient()
client.messages.create(model="something", max_tokens=10, messages=[])
"""
    calls = _detect(source)
    assert calls == []
