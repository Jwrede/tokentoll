# Dev.to Article

---
title: "A model swap costs 15x more and nobody noticed"
published: false
tags: llm, python, devtools, openai
---

## The $47,000 surprise

Here is a one-line code change:

```python
- model="gpt-4o-mini"
+ model="gpt-4o"
```

This looks harmless in a PR. The tests pass. The linter is happy. The reviewer
approves it.

But gpt-4o costs 15x more than gpt-4o-mini. If this endpoint handles 10,000
requests per day, that one-line change just added $10,000/month to your bill.

This is not a hypothetical. Teams have reported LLM cost spikes from $127/week
to $47,000/month from silent model changes.

## The gap in our tooling

We have linters for code quality. We have type checkers for correctness. We have
Infracost for Terraform. But there is nothing that catches LLM cost changes in
code review.

Until now.

## Introducing tokentoll

tokentoll is a CLI tool that statically analyzes your Python code for LLM API
calls and shows you the cost impact of every change.

```bash
pip install tokentoll

# Scan your codebase for LLM calls and their costs
tokentoll scan .

# Show the cost impact of your last commit
tokentoll diff HEAD~1
```

### What it detects

tokentoll uses Python's `ast` module to find calls to:

- **OpenAI**: `chat.completions.create`, `responses.create`
- **Anthropic**: `messages.create`, `messages.stream`
- **Google GenAI**: `models.generate_content`
- **LiteLLM**: `completion`, `acompletion`
- **LangChain**: `ChatOpenAI`, `ChatAnthropic`, `init_chat_model`

For each call, it extracts the model name, max_tokens, and any estimable token
counts from prompt strings. Then it looks up real pricing from a database of
2200+ models (sourced from LiteLLM).

### The diff is where it shines

```
LLM Cost Diff: main..feature-branch
============================================================

+ ADDED    src/agents/rewriter.py:35
           openai | Model: gpt-4o
           Est. cost/call: $0.03 | Monthly: +$26.50

~ MODIFIED src/agents/summarizer.py:42
           openai | Model: gpt-4o -> gpt-4o-mini
           Est. cost/call: $0.03 -> $0.0003 | Monthly: -$26.20

--
Monthly cost impact: +$0.30
  Added: 1 | Changed: 1 | Removed: 0
```

### GitHub Action

tokentoll also works as a GitHub Action that posts cost diffs as PR comments:

```yaml
name: LLM Cost Diff
on:
  pull_request:
    paths: ["**.py"]

permissions:
  pull-requests: write

jobs:
  cost-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Jwrede/tokentoll@v1
```

## How the AST parsing works

The core insight is that LLM API calls follow predictable patterns. An OpenAI
call always looks like:

```python
client.chat.completions.create(model="gpt-4o", ...)
```

tokentoll builds an attribute chain from the AST (`['client', 'chat',
'completions', 'create']`) and checks if it ends with a known pattern. It
also tracks variable assignments to resolve client names:

```python
client = OpenAI()  # tokentoll remembers this
# ...
client.chat.completions.create(...)  # matched via tracked variable
```

Model names are resolved through a tiered lookup: exact match, case-insensitive,
provider prefix stripping (`openai/gpt-4o` -> `gpt-4o`), region prefix stripping
(`us.anthropic.X` -> `anthropic.X`), and date suffix stripping
(`gpt-4o-2024-08-06` -> `gpt-4o`).

## Validated against real codebases

Before calling it done, I ran tokentoll against popular open-source LLM projects:

| Project | LLM Calls Found | Est. Monthly Cost |
|---------|----------------|-------------------|
| LiteLLM | 1,387 | $22,858 |
| LangChain | 429 | $32,186 |
| instructor | 10 | $252 |
| crewAI | 3 | $2 |

**1,834 total calls detected. Zero crashes.** The high monthly estimates assume
1,000 calls/month per call site -- the point is not the absolute number but
the relative cost of different models. A single o1 call site costs 100x more
than a gpt-4o-mini call site.

## What it does NOT do

tokentoll is static analysis. It cannot:

- Estimate costs for dynamic model names (`model=get_model()`)
- Count tokens in computed prompts or template variables
- Predict actual call volume (it assumes a configurable calls-per-month)

These are flagged in the output so you know what to watch for.

## Try it

```bash
pip install tokentoll
tokentoll scan .
```

Zero runtime dependencies. MIT licensed. Works offline with bundled pricing.

GitHub: [github.com/Jwrede/tokentoll](https://github.com/Jwrede/tokentoll)

If you find it useful, a star helps others discover it.
