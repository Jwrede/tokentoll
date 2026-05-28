import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

const client = new OpenAI();

export async function POST(req: NextRequest) {
  const { prompt } = await req.json();
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: 800,
    messages: [{ role: "user", content: prompt }],
  });
  return NextResponse.json({ text: response.choices[0].message.content });
}

export default function Page() {
  return <div>Hello</div>;
}
