import OpenAI from "openai";

const client = new OpenAI();

export async function summarize(input: string) {
  const response = await client.chat.completions.create({
    model: "gpt-4o",
    max_tokens: 1024,
    messages: [{ role: "user", content: input }],
  });
  return response.choices[0].message.content;
}
