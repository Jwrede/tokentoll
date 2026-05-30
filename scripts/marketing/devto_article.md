# Dev.to Article

---
title: "A CI gate that catches LLM cost regressions before they merge"
published: false
tags: llm, python, devtools, openai
---

## The regression nobody catches in code review

Here is a one-line code change:

```python
- model="gpt-4o-mini"
+ model="gpt-4o"
```

It looks like a typo fix. The tests pass, the linter is happy, the reviewer
approves. But `gpt-4o` is roughly 15x more expensive per token than
`gpt-4o-mini`. If that endpoint handles even modest traffic, that one-word
change just compounded into a substantial monthly bill increase that nobody
saw coming.

The same shape applies to `max_tokens` bumps, a new endpoint quietly using
an expensive model, or a langchain init that picks up `gpt-4` from a config
file. None of those land as obvious cost regressions in a normal diff.

## What was missing

We have linters for code quality. We have type checkers for correctness. We
have Infracost for Terraform. Until recently there was nothing focused on
LLM API cost in code review.

## tokentoll

[tokentoll](https://github.com/Jwrede/tokentoll) is an open-source CLI and
GitHub Action that statically analyzes your code for LLM API calls and posts
a PASS/WARN/FAIL verdict on every PR against a policy you control. Recently
merged into [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
(27k stars).

```bash
pip install tokentoll

# Scan a codebase for LLM calls and estimated costs
tokentoll scan .

# Show the cost impact of changes since main
tokentoll diff main..HEAD
```

![tokentoll demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

### What it detects

Python (via the `ast` module):

- **OpenAI**: `chat.completions.create`, `responses.create`, `embeddings.create`
- **Anthropic**: `messages.create`, `messages.stream`
- **Google GenAI**: `models.generate_content`
- **LiteLLM**: `completion`, `acompletion`
- **LangChain**: `ChatOpenAI`, `ChatAnthropic`, `init_chat_model`
- **Zhipu AI**: `ZhipuAiClient`, `ZhipuAI` (GLM models)

JavaScript and TypeScript (via `tree-sitter` with the official JS and TS
grammars; handles `.js`, `.jsx`, `.ts`, `.tsx`):

- **OpenAI Node SDK**: `client.chat.completions.create`, `client.responses.create`, `client.embeddings.create`
- **Anthropic SDK**: `client.messages.create`, `client.messages.stream`
- **Vercel AI SDK**: `generateText`, `streamText`, `generateObject`, `embed`, `embedMany`
- **LangChain.js**: `new ChatOpenAI`, `new ChatAnthropic`, `new ChatGoogleGenerativeAI`

For each detected call, tokentoll extracts the model name, `max_tokens`, and
any token counts it can estimate from prompt strings. It looks up real
pricing from a bundled catalog of 2200+ models sourced from LiteLLM.

### The verdict comment

The output mode that matters most is `--format=github-comment`, which is
what the GitHub Action posts on PRs:

```md
## tokentoll verdict: FAIL

**Blocking findings (2):**

- `src/agent.py:42` per-call cost grew 15.0x (threshold 5x)
- total monthly delta +$812.00 exceeds budget $250.00

> Required action: revert the regression, raise the threshold in `.tokentoll.yml`, or add an exemption.
```

When the PR is clean, the verdict is PASS and the comment shows only the
cost delta table.

### 60-second install

Add `.github/workflows/tokentoll.yml`:

```yaml
name: tokentoll
on:
  pull_request:
    paths:
      - "**.py"
      - "**.ts"
      - "**.tsx"
      - "**.js"
      - "**.jsx"

permissions:
  contents: read
  pull-requests: write

jobs:
  cost-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Jwrede/tokentoll@v0.8.3
        with:
          fail-on-policy-violation: true
```

Then add `.tokentoll.yml` at the repo root:

```yaml
budgets:
  max_monthly_delta_usd: 250
  max_callsite_monthly_usd: 100
  max_relative_increase: 5.0

policies:
  block_unknown_models: true
  fail_on_policy_violation: true
```

Future PRs receive a verdict comment. PRs that exceed the thresholds fail
the workflow.

### Smart defaults for dynamic models

Real codebases load model names from config files, env vars, or runtime
variables that cannot always be resolved statically. Rather than giving up,
tokentoll applies sensible per-SDK defaults:

| SDK | Default Model |
|-----|---------------|
| OpenAI | gpt-4o |
| Anthropic | claude-sonnet-4-20250514 |
| Google GenAI | gemini-2.0-flash |
| Zhipu AI | zai/glm-4.6 |

These are shown as `gpt-4o (default)` in scan output and can be overridden
per-project or per-path via `.tokentoll.yml`. If you would rather skip
default-priced calls entirely, set `skip_dynamic_models: true`.

## How the Python parsing works

The core insight is that LLM API calls follow predictable shapes. An OpenAI
chat completion looks like:

```python
client.chat.completions.create(model="gpt-4o", ...)
```

tokentoll builds the attribute chain from the AST (`['client', 'chat',
'completions', 'create']`) and checks whether it ends with a known SDK
pattern. It also tracks variable assignments so that `client = OpenAI()`
followed by `client.chat...` matches.

### Multi-pass constant propagation

Production codebases rarely write a model name as a literal. tokentoll
iterates a constant propagation pass to a fixed point that resolves
through:

- direct assignments and variable-to-variable chains
- `os.getenv()` and `os.environ.get()` fallbacks
- function default arguments
- class attributes (both class-level and `self.x =` in `__init__`)
- constructor argument propagation (`obj = Cls(val)` so `obj.attr == val`)
- dict literal contents and subscript reads
- `**kwargs` unpacking from a dict

So this chain resolves cleanly:

```python
DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o")

class Config:
    model: str = DEFAULT_MODEL

config = Config()
kwargs = {"model": config.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)
# resolved: model="gpt-4o", max_tokens=2000
```

### Model name resolution

Once a model name is recovered, tokentoll runs tiered lookup against the
pricing catalog: exact match, case-insensitive, provider prefix stripping
(`openai/gpt-4o` to `gpt-4o`), region prefix stripping (`us.anthropic.X` to
`anthropic.X`), and date suffix stripping (`gpt-4o-2024-08-06` to `gpt-4o`).

## How the JS/TS parsing works

JavaScript and TypeScript are parsed with `tree-sitter` using the official
`tree-sitter-javascript` and `tree-sitter-typescript` grammars. The
resolver supports same-file constants, simple object literals,
`process.env.X || "fallback"` and `process.env.X ?? "fallback"` patterns,
and Vercel AI SDK provider wrappers like `openai("gpt-4o")` or
`anthropic("claude-sonnet-4-5")`.

Cross-file import resolution is not in v0.8.3. An imported model constant
from another module is treated as dynamic and falls back to the per-SDK
default.

## Configuration reference

A `.tokentoll.yml` at the repo root customizes behavior:

```yaml
# Per-SDK defaults for dynamic (runtime-resolved) model names
default_models:
  openai: gpt-4o-mini
  anthropic: claude-haiku-3-20240307

# Assumed monthly call volume per call site
calls_per_month: 5000

# Skip cost estimation for dynamic models entirely
skip_dynamic_models: false

# Sensible default excludes (tests/, examples/, docs/, cookbook/, etc.)
# can be opted out of:
use_default_excludes: false

# Per-path overrides (longest prefix match)
overrides:
  - path: src/agents/
    default_model: gpt-4o
    calls_per_month: 10000
```

## Honest limitations

Static analysis cannot reach:

- Models loaded from a database or remote config (these get the per-SDK
  default).
- Actual call volume (the tool assumes a configurable `calls_per_month`).
- Computed prompt content (token estimates use a chars/4 heuristic unless
  tiktoken is installed).
- Cross-module model constants in JS/TS.

Each of these is flagged in the output so the reviewer knows what was
statically resolved versus assumed.

## What is next

- Context-aware call frequency inference (FastAPI route handlers vs CLI
  scripts vs batch jobs) instead of uniform assumptions.
- Cross-file import resolution in JS/TS.
- More public demo material, including a polyglot demo repo wired up to
  the gate with passing and failing example PRs already open.

## Try it

```bash
pip install tokentoll
tokentoll diff main..HEAD
```

GitHub: [github.com/Jwrede/tokentoll](https://github.com/Jwrede/tokentoll)

MIT licensed. No API keys required. No telemetry. Pricing data ships with
the package and works offline.

If you find it useful, a star helps others discover it.
