# LinkedIn Post

A one-word model swap from gpt-4o-mini to gpt-4o is roughly 15x more
expensive per token, and it looks identical to a typo fix in a code diff.
Tests pass, reviewer approves, the bill spikes next month.

tokentoll is an open-source CI gate for LLM API cost regressions. It
statically analyzes Python, JavaScript, and TypeScript for LLM SDK calls,
prices them against a 2200+ model catalog, and posts a PASS/WARN/FAIL
verdict on every pull request against a policy you control. With one flag
set, a budget violation actually blocks the merge.

Recently merged into assafelovic/gpt-researcher (27,000 stars on GitHub).

What it does.
- Detects calls from OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain,
  and Zhipu in Python (via the ast module).
- Detects calls from the OpenAI Node SDK, Anthropic SDK, Vercel AI SDK,
  and LangChain.js in JavaScript and TypeScript (via tree-sitter).
- Resolves model names through variable assignments, env var fallbacks,
  class attributes, and kwargs unpacking, so real-world code with
  indirection still produces useful estimates.
- Evaluates each PR against per-call-site, per-PR, and per-month budgets,
  with rules for blocking unknown models or unbounded cost growth.

How to try it.

  pip install tokentoll
  tokentoll diff main..HEAD

Or as a GitHub Action:

  uses: Jwrede/tokentoll@v0.8.3
  with:
    fail-on-policy-violation: true

Zero telemetry, no API keys required, pricing data ships with the package
and works offline. MIT licensed.

GitHub: https://github.com/Jwrede/tokentoll

#OpenSource #LLM #MLOps #DevTools #AI #MachineLearning #Python
