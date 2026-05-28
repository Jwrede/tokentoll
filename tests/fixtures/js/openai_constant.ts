import OpenAI from "openai";

const client = new OpenAI();
const MODEL = "gpt-4o-mini";
const MAX_TOKENS = 512;

export async function ask(prompt: string) {
  return client.chat.completions.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    messages: [{ role: "user", content: prompt }],
  });
}
