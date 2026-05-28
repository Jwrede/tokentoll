import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

export async function answer(prompt: string) {
  const msg = await client.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 4096,
    messages: [{ role: "user", content: prompt }],
  });
  return msg.content;
}

export async function stream(prompt: string) {
  return client.messages.stream({
    model: "claude-haiku-3-5-20241022",
    max_tokens: 2048,
    messages: [{ role: "user", content: prompt }],
  });
}
