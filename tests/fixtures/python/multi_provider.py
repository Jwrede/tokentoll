from openai import OpenAI
from anthropic import Anthropic
import litellm

openai_client = OpenAI()
anthropic_client = Anthropic()

r1 = openai_client.chat.completions.create(
    model="gpt-4o",
    max_tokens=2000,
    messages=[{"role": "user", "content": "Hello"}],
)

r2 = anthropic_client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
    system="You are a helpful assistant.",
)

r3 = litellm.completion(
    model="gpt-4o-mini",
    max_tokens=500,
    messages=[{"role": "user", "content": "Quick question"}],
)
