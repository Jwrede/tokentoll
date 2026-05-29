import Anthropic from "@anthropic-ai/sdk";

class ToolRunner {
  client: Anthropic;

  constructor() {
    this.client = new Anthropic();
  }

  async run(prompt: string) {
    return this.client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 2048,
      messages: [{ role: "user", content: prompt }],
    });
  }

  async runBeta(prompt: string) {
    return this.client.beta.messages.create({
      model: "claude-haiku-3-5-20241022",
      max_tokens: 1024,
      messages: [{ role: "user", content: prompt }],
    });
  }
}

export { ToolRunner };
