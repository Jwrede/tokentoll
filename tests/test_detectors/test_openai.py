from tokentoll.core.models import CallType
from tokentoll.scanner.python_scanner import scan_source


def _detect(source: str) -> list:
    return scan_source(source, "test.py")


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


def test_dynamic_model():
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


def test_variable_model_resolution():
    source = """
from openai import OpenAI
client = OpenAI()
MODEL = "gpt-4o"
client.chat.completions.create(model=MODEL, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].model_is_literal is False


def test_variable_max_tokens_resolution():
    source = """
from openai import OpenAI
client = OpenAI()
MAX_TOKENS = 2000
client.chat.completions.create(model="gpt-4o", max_tokens=MAX_TOKENS, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].max_tokens == 2000


def test_os_getenv_fallback():
    source = """
import os
from openai import OpenAI
client = OpenAI()
model = os.getenv("MODEL", "gpt-4o-mini")
client.chat.completions.create(model=model, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"
    assert calls[0].model_is_literal is False


def test_os_environ_get_fallback():
    source = """
import os
from openai import OpenAI
client = OpenAI()
model = os.environ.get("OPENAI_MODEL", "gpt-4o")
client.chat.completions.create(model=model, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_function_default_model():
    source = """
from openai import OpenAI
client = OpenAI()
def call_llm(model="gpt-4o", max_tokens=1000):
    return client.chat.completions.create(model=model, max_tokens=max_tokens, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].max_tokens == 1000


def test_kwargs_splatting():
    source = """
from openai import OpenAI
client = OpenAI()
kwargs = {"model": "gpt-4o", "max_tokens": 2000}
client.chat.completions.create(**kwargs)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"
    assert calls[0].max_tokens == 2000


def test_kwargs_subscript_assignment():
    source = """
from openai import OpenAI
client = OpenAI()
kwargs = {}
kwargs["model"] = "gpt-4o-mini"
client.chat.completions.create(**kwargs)
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"


def test_class_attribute_default():
    source = """
from openai import OpenAI

class Config:
    model: str = "gpt-4o"

client = OpenAI()
config = Config()
client.chat.completions.create(model=config.model, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_constructor_arg_propagation():
    source = """
import litellm

DEFAULT_MODEL = "gpt-4o"

class LLMClient:
    def __init__(self, model_name):
        self.name = model_name

client = LLMClient(DEFAULT_MODEL)
litellm.completion(model=client.name, messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_module_level_import():
    source = """
import openai
openai.chat.completions.create(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_lazy_import():
    source = """
def call_llm():
    from openai import OpenAI
    client = OpenAI()
    return client.chat.completions.create(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_factory_client():
    source = """
from openai.types.chat import ChatCompletion
client = get_openai_client()
client.chat.completions.create(model="gpt-4o", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o"


def test_method_parameter_client():
    source = """
import openai
def call(self, client):
    return client.chat.completions.create(model="gpt-4o-mini", messages=[])
"""
    calls = _detect(source)
    assert len(calls) == 1
    assert calls[0].model == "gpt-4o-mini"


def test_no_openai_import():
    source = """
import requests
requests.get("https://example.com")
"""
    calls = _detect(source)
    assert len(calls) == 0


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
