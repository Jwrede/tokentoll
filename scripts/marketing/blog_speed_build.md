# Blog Post: How I built Infracost for LLM spend in a day

---
title: "How I built Infracost for LLM spend in a day"
published: false
tags: llm, python, devtools, building
---

## The idea

Every team using LLM APIs has the same problem: cost surprises. A model swap,
a new endpoint, a forgotten max_tokens parameter, and suddenly the bill spikes.

Infracost solved this for Terraform by analyzing code diffs and showing cloud
cost impact on PRs. Nobody had built the LLM equivalent.

So I did, in a day.

![tokentoll demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

## The architecture

tokentoll has five layers:

1. **Scanner**: walks Python files, dispatches to detectors
2. **Detectors**: one per SDK (OpenAI, Anthropic, Google, LiteLLM, LangChain),
   each knows how to find API calls in an AST
3. **Pricing engine**: model name -> cost per token, with tiered resolution,
   per-SDK defaults for dynamic models, and a local cache
4. **Diff engine**: matches old vs new calls by file + line proximity
5. **Output formatters**: table (CLI), markdown (PR comment), JSON

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

- **Per-SDK defaults.** When a model name is dynamic (loaded from config or
  env vars at runtime), tokentoll applies the most common model for that SDK:
  gpt-4o for OpenAI, claude-sonnet for Anthropic, gemini-flash for Google.
  This means you always get cost estimates, even for dynamic code.

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

## Multi-pass constant propagation

The second hardest part: model names are rarely string literals. They flow
through variables, class attributes, config objects, and `**kwargs`.

```python
DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o")

class Config:
    model: str = DEFAULT_MODEL

config = Config()
kwargs = {"model": config.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)
# tokentoll resolves: model="gpt-4o", max_tokens=2000
```

The engine iterates to a fixed point, following: variable assignments,
`os.getenv()` fallbacks, function defaults, class attribute defaults,
constructor argument propagation, dict contents, and `**kwargs` unpacking.

## Configuration

A `.tokentoll.yml` file lets you tune behavior per project:

```yaml
calls_per_month: 5000
default_models:
  openai: gpt-4o-mini
  anthropic: claude-haiku-3-20240307
overrides:
  - path: tests/
    calls_per_month: 100
```

Per-path overrides use longest-prefix matching, so you can set different
assumptions for test code, agent pipelines, and batch jobs.

## Validation

Before calling it done, I ran tokentoll against twenty real codebases including
NadirClaw, PraisonAI, agentops, swarms, honcho, atomic-agents, and others. It
correctly detected OpenAI, Anthropic, Google, and LiteLLM calls across all of
them, with per-SDK default models producing sensible cost estimates even for
projects that load model names from config at runtime.

## Try it

```bash
pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1
```

GitHub: [github.com/Jwrede/tokentoll](https://github.com/Jwrede/tokentoll)
