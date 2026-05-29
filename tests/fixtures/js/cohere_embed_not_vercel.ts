// langchain-cohere style: client.embed(request). Must NOT be picked up by
// the Vercel AI SDK detector, which only matches bare `embed(...)` from
// the @ai-sdk/* import.
import { CohereClient } from "cohere-ai";

class CohereEmbeddings {
  client: CohereClient;

  constructor() {
    this.client = new CohereClient({});
  }

  async embed(texts: string[]) {
    return this.client.embed({ texts, model: "embed-english-v3.0" });
  }

  async embedMany(items: string[]) {
    return this.client.embedMany(items);
  }
}

export { CohereEmbeddings };
