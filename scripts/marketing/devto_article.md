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

![tokentoll demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

### What it detects

tokentoll uses Python's `ast` module to find calls to:

- **OpenAI**: `chat.completions.create`, `responses.create`
- **Anthropic**: `messages.create`, `messages.stream`
- **Google GenAI**: `models.generate_content`
- **LiteLLM**: `completion`, `acompletion`
- **LangChain**: `ChatOpenAI`, `ChatAnthropic`, `init_chat_model`
- **Zhipu AI**: `ZhipuAiClient`, `ZhipuAI` (GLM models)

For each call, it extracts the model name, max_tokens, and any estimable token
counts from prompt strings. Then it looks up real pricing from a database of
2200+ models (sourced from LiteLLM).

### Smart defaults for dynamic models

Real codebases often load model names from config files or environment variables
that can't be resolved at analysis time. Instead of giving up, tokentoll applies
sensible per-SDK defaults:

| SDK | Default Model |
|-----|---------------|
| OpenAI | gpt-4o |
| Anthropic | claude-sonnet-4-20250514 |
| Google GenAI | gemini-2.0-flash |
| Zhipu AI | zai/glm-4.6 |

These are shown as `gpt-4o (default)` in scan output. You can override them
per-project or per-path via a `.tokentoll.yml` config file.

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
  contents: read
  pull-requests: write

jobs:
  cost-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Jwrede/tokentoll@v0.6.1
```

### Configuration

A `.tokentoll.yml` file lets you customize per-project behavior:

```yaml
calls_per_month: 5000

default_models:
  openai: gpt-4o-mini
  anthropic: claude-haiku-3-20240307

overrides:
  - path: tests/
    calls_per_month: 100
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

### Multi-pass constant propagation

Real codebases rarely pass string literals directly. Model names flow through
variables, class attributes, config objects, and `**kwargs`. tokentoll uses a
multi-pass constant propagation engine that iterates to a fixed point:

```python
DEFAULT_MODEL = "gpt-4o"

class Config:
    model: str = DEFAULT_MODEL

config = Config()
kwargs = {"model": config.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)  # resolved: model="gpt-4o", max_tokens=2000
```

It follows: variable assignments, `os.getenv()` fallbacks, function defaults,
class attribute defaults, constructor argument propagation (`obj = Cls(val)` ->
`self.attr`), dict contents, and `**kwargs` unpacking.

Model names are then resolved through a tiered pricing lookup: exact match,
case-insensitive, provider prefix stripping (`openai/gpt-4o` -> `gpt-4o`),
region prefix stripping (`us.anthropic.X` -> `anthropic.X`), and date suffix
stripping (`gpt-4o-2024-08-06` -> `gpt-4o`).

## What it does NOT do

tokentoll is static analysis. It cannot:

- Resolve models loaded from external config files or databases at runtime
  (these get per-SDK default pricing instead)
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
