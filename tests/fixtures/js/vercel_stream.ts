import { streamText, embed } from "ai";
import { openai } from "@ai-sdk/openai";

export async function stream(input: string) {
  return streamText({
    model: openai("gpt-4o-mini"),
    prompt: input,
    maxOutputTokens: 4096,
  });
}

export async function embedOne(input: string) {
  return embed({
    model: openai.embedding("text-embedding-3-small"),
    value: input,
  });
}
