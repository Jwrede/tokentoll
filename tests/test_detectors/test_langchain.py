import ast

from tokentoll.core.models import CallType
from tokentoll.detectors.langchain_detector import LangChainDetector


def _detect(source: str) -> list:
    tree = ast.parse(source)
    d = LangChainDetector()
    if not d.can_handle(tree, source):
        return []
    return d.detect(tree, "test.py")


def test_chat_openai():
    source = """
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", max_tokens=1000)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].max_tokens == 1000
    assert calls[0].sdk == "langchain"
    assert calls[0].call_type == CallType.CHAT_COMPLETION


def test_chat_anthropic():
    source = """
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=512)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "claude-sonnet-4-20250514"


def test_init_chat_model():
    source = """
from langchain.chat_models import init_chat_model
llm = init_chat_model("gpt-4o-mini")
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"


def test_no_langchain_import():
    source = """
import openai
openai.chat.completions.create(model="gpt-4o", messages=[])
"""
    tree = ast.parse(source)
    d = LangChainDetector()
    assert not d.can_handle(tree, source)
