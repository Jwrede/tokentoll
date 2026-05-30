# r/devops Post

## Title

GitHub Action that comments on PRs with LLM API cost impact (like Infracost for Terraform, but for model calls)

## Body

If your team uses LLM APIs, you've probably had a surprise bill from a model swap that slipped through review. A `gpt-4o-mini` to `gpt-4o` change is 15x more expensive and looks like a one-word diff.

**tokentoll** is a GitHub Action that posts a PASS/WARN/FAIL verdict on every PR against a policy you control. Recently merged into assafelovic/gpt-researcher (27k stars).

```yaml
name: LLM Cost Diff
on:
  pull_request:
    paths: ["**.py", "**.ts", "**.tsx", "**.js", "**.jsx"]

permissions:
  contents: read
  pull-requests: write

jobs:
  cost-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Jwrede/tokentoll@v0.8.3
        with:
          fail-on-policy-violation: true
```

The PR comment shows:

```
~ MODIFIED src/agents/summarizer.py:42
  openai | Model: gpt-4o-mini -> gpt-4o
  Monthly: +$26.20 (15x increase)

+ ADDED src/pipeline/rewriter.py:35
  openai | Model: gpt-4o
  Monthly: +$26.50

Monthly cost impact: +$52.70
```

Under the hood it uses Python AST and tree-sitter for JS/TS to find LLM API calls (OpenAI, Anthropic, Google, LiteLLM, LangChain, Zhipu, Vercel AI SDK, LangChain.js), resolve model names through variable assignments and env vars, and look up real pricing for 2200+ models.

Configurable via `.tokentoll.yml` with path exclusions and per-path overrides. Zero runtime dependencies. Action is pinned to a SHA.

GitHub: https://github.com/Jwrede/tokentoll

Anyone else dealing with LLM cost visibility in CI? Curious what your setup looks like.

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one SECOND (medium audience, ~350K)
- At least 24 hours after r/Python post
- Frame as infrastructure/guardrail, not a Python library
