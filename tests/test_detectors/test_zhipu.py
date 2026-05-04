from tokentoll.core.models import CallType
from tokentoll.scanner.python_scanner import scan_source


def _detect(source: str) -> list:
    return scan_source(source, "test.py")


def test_zhipuai_client_basic():
    source = """
from zai import ZhipuAiClient
client = ZhipuAiClient()
client.chat.completions.create(model="glm-4.6", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].sdk == "zai"
    assert calls[0].model == "glm-4.6"
    assert calls[0].call_type == CallType.CHAT_COMPLETION


def test_zhipuai_legacy_client():
    source = """
from zhipuai import ZhipuAI
client = ZhipuAI()
client.chat.completions.create(model="glm-4.5", max_tokens=512, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].sdk == "zai"
    assert calls[0].model == "glm-4.5"
    assert calls[0].max_tokens == 512


def test_zhipu_self_attribute_pattern():
    # Mirrors xagent's zhipu.py file structure that triggered the false
    # positive in v0.4.0/v0.5.0/v0.5.1.
    source = """
from zai import ZhipuAiClient

class ZhipuChat:
    def __init__(self):
        self._client = ZhipuAiClient()

    def call(self):
        return self._client.chat.completions.create(model="glm-4", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].sdk == "zai"
    # Critical: must not also be detected by the OpenAI detector.
    assert all(c.sdk == "zai" for c in calls)


def test_zhipu_is_not_double_counted_as_openai():
    source = """
from zai import ZhipuAiClient
client = ZhipuAiClient()
client.chat.completions.create(model="glm-4.6", messages=[])
"""
    calls = _detect(source)
    sdks = [c.sdk for c in calls]
    assert sdks == ["zai"]


def test_no_zai_import_no_detection():
    source = """
import requests
requests.post("https://api.example.com")
"""
    calls = _detect(source)
    assert calls == []
