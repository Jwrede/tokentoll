import OpenAI from "openai";

const client = new OpenAI();
const MODEL = "gpt-4o";

type ModelName = string;

export async function asCast(prompt: string) {
  return client.chat.completions.create({
    model: "gpt-4o-mini" as ModelName,
    max_tokens: 1024 as number,
    messages: [{ role: "user", content: prompt }],
  });
}

export async function satisfies(prompt: string) {
  return client.chat.completions.create({
    model: "gpt-4o" satisfies ModelName,
    messages: [{ role: "user", content: prompt }],
  });
}

export async function nonNull(prompt: string) {
  return client.chat.completions.create({
    model: MODEL!,
    messages: [{ role: "user", content: prompt }],
  });
}

export async function parens(prompt: string) {
  return client.chat.completions.create({
    model: ("gpt-4o-mini"),
    messages: [{ role: "user", content: prompt }],
  });
}

export async function legacyAssertion(prompt: string) {
  return client.chat.completions.create({
    model: <ModelName>"claude-not-really",
    messages: [{ role: "user", content: prompt }],
  });
}
