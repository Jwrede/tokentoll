import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

const chat = new ChatOpenAI({
  model: "gpt-4o",
  maxTokens: 2048,
});

const claude = new ChatAnthropic({
  model: "claude-haiku-3-5-20241022",
  maxTokens: 1024,
});

const gemini = new ChatGoogleGenerativeAI({
  model: "gemini-2.0-flash",
});

export { chat, claude, gemini };
