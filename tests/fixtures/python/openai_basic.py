from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello world"}],
)

response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=500,
    messages=[{"role": "user", "content": "Summarize this"}],
)

response3 = client.responses.create(
    model="gpt-4o",
    input="What is the meaning of life?",
)
