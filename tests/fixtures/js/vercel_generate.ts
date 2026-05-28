import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { anthropic } from "@ai-sdk/anthropic";

export async function summarize(input: string) {
  const { text } = await generateText({
    model: openai("gpt-4o"),
    prompt: input,
    maxOutputTokens: 1024,
  });
  return text;
}

export async function rewrite(input: string) {
  const { text } = await generateText({
    model: anthropic("claude-sonnet-4-5"),
    prompt: input,
  });
  return text;
}
