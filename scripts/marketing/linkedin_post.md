# LinkedIn Post

A single model swap from gpt-4o-mini to gpt-4o increases LLM API costs by 15x.
These changes are invisible in normal code review.

tokentoll is an open-source CLI tool and GitHub Action that statically
analyzes Python, JavaScript, and TypeScript for LLM API calls and posts a
PASS/WARN/FAIL verdict on every PR.

Just merged into assafelovic/gpt-researcher (27k stars).

How it works:
- Parses Python via the ast module, JS/TS via tree-sitter
- Detects calls to OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu, Vercel AI SDK, LangChain.js
- Looks up real pricing data (2200+ models)
- Resolves dynamic model names through variable assignments, env vars, class attributes, kwargs unpacking
- Scores every PR against a policy you control (max monthly delta, max relative increase, block unknown models)

Think Infracost, but for LLM API spend.

Zero runtime dependencies on the Python side. MIT licensed. Configurable via
.tokentoll.yml for per-project and per-path overrides, with sensible default
exclusions for tests, examples, docs, and cookbook code.

Next: context-aware call frequency inference (route handlers vs scripts vs
batch jobs) and cross-file import resolution for JS/TS.

pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1

GitHub: https://github.com/Jwrede/tokentoll

#OpenSource #LLM #MLOps #DevTools #AI #MachineLearning #Python
