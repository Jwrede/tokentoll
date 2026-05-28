import OpenAI from "openai";

const client = new OpenAI();

export async function chat(input: string) {
  return client.chat.completions.create({
    model: process.env.OPENAI_MODEL || "gpt-4o",
    max_tokens: Number(process.env.MAX_TOKENS) ?? 2048,
    messages: [{ role: "user", content: input }],
  });
}

export async function nullish(input: string) {
  return client.chat.completions.create({
    model: process.env.MODEL2 ?? "gpt-4o-mini",
    messages: [{ role: "user", content: input }],
  });
}
