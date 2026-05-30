# Show HN: Tokentoll, a CI gate for LLM API cost regressions

## Title (for HN submit box)

Show HN: Tokentoll, a CI gate for LLM API cost regressions

## URL

https://github.com/Jwrede/tokentoll

## First comment (post immediately after submitting)

Quick rundown of what tokentoll is and what it isn't.

What it is. A CLI plus GitHub Action that parses Python (ast) and JavaScript/TypeScript (tree-sitter) for LLM SDK calls, prices them against a bundled 2200+ model catalog from LiteLLM, and posts a PASS/WARN/FAIL verdict on every PR against a policy you configure. With `fail-on-policy-violation: true` the check exits non-zero on FAIL, so a budget violation actually blocks the merge.

The hook. A one-word model swap from gpt-4o-mini to gpt-4o is roughly 15x more expensive per token and looks identical to a typo fix in a normal diff. Same shape for a max_tokens bump or a new endpoint calling an expensive model.

Detection today.

  - Python: OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu
  - JS/TS: OpenAI Node SDK, Anthropic SDK, Vercel AI SDK, LangChain.js

Model names are resolved through variable assignments, env var fallbacks (os.getenv, process.env), class attributes, kwargs / object literal unpacking, and Vercel AI SDK provider wrappers like `openai("gpt-4o")`. Multi-pass constant propagation iterates to a fixed point.

Policy rules.

  - max_monthly_delta_usd: aggregate cap
  - max_callsite_monthly_usd: per-call-site cap
  - max_relative_increase: per-call cost multiplier cap
  - block_unknown_models: any unpriced or unresolved model is a violation

There's also an MCP server (`tokentoll-mcp`) so Claude Code or other MCP hosts can run scan and diff inside an agent conversation.

Honest limitations.

  - Static analysis only. Models loaded from a database or remote config fall back to a per-SDK default and the call site is flagged.
  - Token estimates use a chars/4 heuristic unless tiktoken is installed.
  - JS/TS resolution is same-file. An imported model constant from another module is treated as dynamic.

Adoption so far is mostly one largish repo (assafelovic/gpt-researcher, 27k stars) plus a few smaller AI apps. v0.8.3 shipped today and fixes a diff-matching bug I caught while running tokentoll against gpt-researcher's open PRs: shifted call sites were getting reported as REMOVED + ADDED pairs even when the call shape did not change.

Install:

    pip install tokentoll
    tokentoll scan .
    tokentoll diff main..HEAD

Would value pointers to SDK patterns I'm missing or pathological repos worth testing against.

## Posting notes

- Best time: Sunday 00:00-02:00 UTC (Saturday evening US Pacific, lowest competition)
- Weekday alternative: Tuesday-Thursday 14:00-17:00 UTC
- Link post format (title + URL, no body text)
- Post the first comment immediately after submitting
- Respond to every comment within an hour
- Do NOT frame as "AI tool", frame as developer cost visibility
- Do NOT ask anyone to upvote via direct link (HN detects voting rings)
