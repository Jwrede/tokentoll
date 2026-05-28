import OpenAI from "openai";

const client = new OpenAI();

export async function dynamicCall(model: string, prompt: string) {
  return client.chat.completions.create({
    model: model,
    messages: [{ role: "user", content: prompt }],
  });
}
