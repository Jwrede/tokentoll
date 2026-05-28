import OpenAI from "openai";

const client = new OpenAI();

export async function handle(input: string) {
  return client.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: 1024,
    messages: [{ role: "user", content: input }],
  });
}
