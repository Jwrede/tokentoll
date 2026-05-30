# r/mlops Post

## Title

Static analysis CI gate for LLM cost regressions: PASS/WARN/FAIL on every PR

## Body

The cost regression pattern I keep seeing in PR review: a model parameter changes, the code logic is fine, the test suite passes, and the LLM bill goes up. Cost is invisible in a diff. Infracost solved the equivalent for Terraform but nothing focused on LLM API calls existed.

**tokentoll** is a CI gate for this. It statically analyzes Python (`ast` module), JavaScript, and TypeScript (`tree-sitter` with the official JS and TS grammars), prices every LLM SDK call against a 2200+ model catalog from LiteLLM, and posts a PASS/WARN/FAIL verdict on every PR against a policy you define.

Detection coverage today:

- Python: OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu
- JS/TS: OpenAI Node SDK, Anthropic SDK, Vercel AI SDK, LangChain.js

Policy rules (independent, each enabled by setting a value):

- `max_monthly_delta_usd`: total estimated monthly delta cap
- `max_callsite_monthly_usd`: per-call-site cap
- `max_relative_increase`: per-call cost multiplier cap
- `block_unknown_models`: any unpriced or unresolved model is a violation

Example FAIL output:

```md
## tokentoll verdict: FAIL

Blocking findings (2):

- src/agent.py:42 per-call cost grew 15.0x (threshold 5x)
- total monthly delta +$812.00 exceeds budget $250.00
```

There is also an MCP server (`tokentoll-mcp`) so Claude Code and other MCP hosts can run `scan` and `diff` from inside an agent conversation.

Honest limitations.

- Static analysis only. Models loaded from a database or remote config cannot be resolved; tokentoll falls back to a per-SDK default and marks the call as a default lookup.
- Token estimates use a chars/4 heuristic unless tiktoken is installed (`pip install tokentoll[tiktoken]`).
- Monthly estimates assume uniform call volume per call site, configurable per project or per path via `.tokentoll.yml`.
- JS/TS model resolution is same-file only. Cross-module import resolution is on the roadmap.

Adoption: merged into `assafelovic/gpt-researcher` (27k stars), plus a couple of smaller AI apps. v0.8.3 (shipped today) fixes a diff-matching bug that surfaced phantom REMOVED + ADDED pairs when calls shifted lines during refactor.

Install:

    pip install tokentoll
    tokentoll diff main..HEAD

GitHub: https://github.com/Jwrede/tokentoll

Curious how others tackle this in pipelines today. Runtime tracing? Budgets from the billing API? Manual review?

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one THIRD (smallest audience, ~67K, but highly targeted)
- At least 24 hours after r/devops post
- Frame as a pipeline stage, not a Python library
