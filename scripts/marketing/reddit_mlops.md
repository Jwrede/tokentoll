# r/mlops Post

## Title

A gpt-4o-mini to gpt-4o swap costs 15x more and is invisible in code review. I built a CI step that catches it.

## Body

I've seen this happen twice now: someone changes a model parameter in a PR, it passes review because the code logic is fine, and the LLM bill spikes. The problem is that cost is not visible in a diff.

**tokentoll** is a CLI (and GitHub Action) that statically analyzes Python, JS, and TS for LLM API calls, estimates their cost using real pricing data, and posts a PASS/WARN/FAIL verdict on every PR. Recently merged into assafelovic/gpt-researcher (27k stars).

```yaml
# Add to your CI pipeline
- uses: Jwrede/tokentoll@v0.8.3
  with:
    fail-on-policy-violation: true
```

It posts a comment on the PR showing what changed:

```
~ MODIFIED src/agents/summarizer.py:42
  openai | Model: gpt-4o-mini -> gpt-4o
  Monthly: +$26.20 per call site (15x increase)

+ ADDED src/pipeline/embedder.py:18
  openai | Model: text-embedding-3-large
  Monthly: +$4.80
```

It detects calls to OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, and Zhipu in Python via AST, plus the OpenAI Node SDK, Anthropic SDK, Vercel AI SDK, and LangChain.js in JS/TS via tree-sitter. Model names are resolved through variable assignments, env var fallbacks, class attributes, and `**kwargs` / object literal unpacking.

You can configure it per-path via `.tokentoll.yml`:

```yaml
exclude:
  - tests/
  - examples/

overrides:
  - path: src/agents/
    calls_per_month: 10000
```

Zero runtime dependencies. Pricing data covers 2200+ models (sourced from LiteLLM). Works offline.

Next up: context-aware frequency inference (auto-detect route handlers vs batch jobs vs scripts instead of assuming uniform call volume), and cross-file import resolution for JS/TS.

GitHub: https://github.com/Jwrede/tokentoll

How are you currently tracking LLM cost changes before they hit production?

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one THIRD (smallest audience, ~67K, but highly targeted)
- At least 24 hours after r/devops post
- Frame as a pipeline stage, not a Python library
