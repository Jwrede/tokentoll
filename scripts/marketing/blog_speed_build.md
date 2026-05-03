# Blog Post: How I built Infracost for LLM spend in a day

---
title: "How I built Infracost for LLM spend in a day"
published: false
tags: llm, python, devtools, building
---

## The idea

Every team using LLM APIs has the same problem: cost surprises. A model swap,
a new endpoint, a forgotten max_tokens parameter -- and suddenly the bill
spikes.

Infracost solved this for Terraform by analyzing code diffs and showing cloud
cost impact on PRs. Nobody had built the LLM equivalent.

So I did, in a day.

## The architecture

tokentoll has five layers:

1. **Scanner** -- walks Python files, dispatches to detectors
2. **Detectors** -- one per SDK (OpenAI, Anthropic, Google, LiteLLM, LangChain),
   each knows how to find API calls in an AST
3. **Pricing engine** -- model name -> cost per token, with tiered resolution
   and a local cache
4. **Diff engine** -- matches old vs new calls by file + line proximity
5. **Output formatters** -- table (CLI), markdown (PR comment), JSON

The key design decisions:

- **Zero runtime dependencies.** Everything uses stdlib: `ast` for parsing,
  `json` for data, `subprocess` for git, `argparse` for CLI, `urllib` for
  fetching prices. This makes installation instant and the tool trustworthy.

- **Detectors are pluggable.** Adding a new SDK means writing one file that
  implements `can_handle()` and `detect()`. No changes to the scanner or
  pipeline.

- **Pricing is cached locally.** On first run, tokentoll fetches LiteLLM's
  pricing database (2200+ models) and caches it to `~/.tokentoll/`. It warns
  if the cache is stale and errors if it is very old.

## The hardest part

Model name resolution. Users write `model="gpt-4o"` in their code, but the
pricing database has entries like `gpt-4o`, `openai/gpt-4o`,
`gpt-4o-2024-08-06`, `azure/gpt-4o`, etc.

The solution is a tiered resolution chain:
1. Exact match
2. Case-insensitive match
3. Add SDK prefix and match (`openai/gpt-4o`)
4. Strip provider prefix from DB keys and match
5. Strip region prefix (`us.`, `eu.`, `apac.`)
6. Strip date suffix (`-2024-08-06`, `-20240806`)

This handles 95%+ of real-world model names I found scanning open-source
projects.

## Validation

Before calling it done, I ran tokentoll against five real codebases:

- **LiteLLM** (1,387 calls detected) -- the ultimate stress test
- **LangChain** (429 calls) -- cross-SDK detection
- **instructor** (10 calls) -- OpenAI patterns
- **promptfoo** (5 calls) -- mixed patterns
- **crewAI** (3 calls) -- deeply nested code

1,834 total calls detected. Zero crashes. One bug found (Bedrock region
prefix resolution), fixed in 10 minutes.

## What I'd do differently

If I were building this as a product (not a portfolio project):

- **TypeScript/JS support.** Many LLM apps are Node.js. Tree-sitter would
  handle the parsing.
- **Config file.** Per-project overrides for call volume assumptions and
  model aliases.
- **Historical trending.** Store scan results over time, show cost trend
  charts.

## Try it

```bash
pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1
```

GitHub: [github.com/Jwrede/tokentoll](https://github.com/Jwrede/tokentoll)
