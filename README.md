# tokentoll

> Catch LLM cost changes in code review. Infracost for LLM spend.

[![CI](https://github.com/Jwrede/tokentoll/actions/workflows/ci.yml/badge.svg)](https://github.com/Jwrede/tokentoll/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/tokentoll)](https://pypi.org/project/tokentoll/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A CLI tool and GitHub Action that statically analyzes your code for LLM API calls,
estimates their cost, and shows you the cost impact of every change in your
terminal or as a PR comment. Zero runtime dependencies.

## The Problem

A single model swap from `gpt-4o-mini` to `gpt-4o` increases costs **15x**.
A new API call in a hot path can add **$10,000/month** to your bill.
These changes hide in normal code review.

tokentoll finds LLM API calls in your code, estimates their cost,
and shows you the cost impact of every change before it hits production.

## Quick Start

```bash
pip install tokentoll

# Scan current directory for LLM API calls and their costs
tokentoll scan .

# Show cost impact of your last commit
tokentoll diff HEAD~1

# Compare two branches
tokentoll diff main..feature-branch
```

## GitHub Action

```yaml
name: LLM Cost Diff
on:
  pull_request:
    paths:
      - "**.py"

permissions:
  pull-requests: write

jobs:
  cost-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: Jwrede/tokentoll@v0.5.0
```

## What It Detects

| SDK | Patterns | Status |
|-----|----------|--------|
| OpenAI | `chat.completions.create`, `responses.create` | Supported |
| Anthropic | `messages.create`, `messages.stream` | Supported |
| Google GenAI | `models.generate_content` | Supported |
| LiteLLM | `completion`, `acompletion` | Supported |
| LangChain | `ChatOpenAI`, `ChatAnthropic`, `init_chat_model` | Supported |
| JS/TS SDKs | | Planned |

## Example Output

### `tokentoll scan`

```
LLM API Calls Detected
============================================================

File: src/agents/summarizer.py
  Line 42: openai client.chat.completions.create
           Model: gpt-4o | Max tokens: 4096
           Est. cost/call: $0.03 | Monthly (1000 calls/month per call site): $26.50

  Line 78: openai client.chat.completions.create
           Model: gpt-4o-mini | Max tokens: 1000
           Est. cost/call: $0.000301 | Monthly (1000 calls/month per call site): $0.30

--
Total estimated monthly cost: $26.80
  1000 calls/month per call site
```

### `tokentoll diff`

```
LLM Cost Diff: main..feature-branch
============================================================

+ ADDED    src/agents/rewriter.py:35
           openai | Model: gpt-4o
           Est. cost/call: $0.03 | Monthly: +$26.50

~ MODIFIED src/agents/summarizer.py:42
           openai | Model: gpt-4o -> gpt-4o-mini
           Est. cost/call: $0.03 -> $0.000301 | Monthly: -$26.20

--
Monthly cost impact: +$0.30
  Added: 1 | Changed: 1 | Removed: 0
  1000 calls/month per call site
```

## How It Works

```
  Source Code (.py files)
         |
         v
  +-------------+     +------------------+
  | AST Scanner |---->| SDK Detectors    |
  | (ast.parse) |     | OpenAI, Anthropic|
  +-------------+     | Google, LiteLLM  |
                       | LangChain        |
                       +------------------+
                              |
                              v
                       +------------------+
                       | Pricing Engine   |
                       | 2200+ models     |
                       | Auto-cached      |
                       +------------------+
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
           +------------+         +-------------+
           | Scan Report|         | Diff Engine  |
           | (costs)    |         | (old vs new) |
           +------------+         +-------------+
                  |                       |
                  v                       v
           +------------+         +-------------+
           | Table/JSON |         | Table/JSON/  |
           |            |         | PR Comment   |
           +------------+         +-------------+
```

1. Parses Python files using the `ast` module to find LLM API calls
2. Multi-pass constant propagation resolves model names through variables,
   `os.getenv()` fallbacks, class attributes, constructor args, dict contents,
   and `**kwargs` unpacking
3. Looks up pricing from a local cache (sourced from LiteLLM, 2200+ models)
4. For diff mode: compares calls between two git refs and computes the cost delta
5. Outputs a cost report as a table, JSON, or GitHub PR comment

## CLI Reference

```
tokentoll scan [PATH...] [--format table|json|markdown] [--calls-per-month N] [--config PATH]
tokentoll diff [REF] [--base REF] [--head REF] [--format table|json|markdown|github-comment] [--config PATH]
tokentoll update    # Update bundled pricing data
```

## Pricing Data

Pricing is bundled and works offline. To update to the latest prices:

```bash
tokentoll update
```

Pricing data is sourced from LiteLLM's `model_prices_and_context_window.json`
and covers 300+ models across OpenAI, Anthropic, Google, AWS Bedrock,
Azure, and more.

## Dynamic Model Defaults

When tokentoll encounters a call where the model name is a variable it cannot resolve,
it applies a sensible per-SDK default so you still get cost estimates:

| SDK | Default Model |
|-----|---------------|
| OpenAI | `gpt-4o` |
| Anthropic | `claude-sonnet-4-20250514` |
| Google GenAI | `gemini-2.0-flash` |
| LiteLLM | `gpt-4o` |
| LangChain | `gpt-4o` |

These defaults are shown as `gpt-4o (default)` in scan output. You can override
them per-project or per-path using a `.tokentoll.yml` config file (see below).

## Configuration

Create a `.tokentoll.yml` in your project root to customize behavior.
tokentoll automatically finds this file by walking up from the scanned directory.

```yaml
# Default model for all dynamic (unresolved) calls
default_model: gpt-4o

# Per-SDK defaults (override the built-in defaults above)
default_models:
  openai: gpt-4o-mini
  anthropic: claude-haiku-3-20240307

# Assumed calls per month per call site
calls_per_month: 5000

# Per-path overrides (longest prefix match)
overrides:
  - path: tests/
    calls_per_month: 100
  - path: src/agents/
    default_model: gpt-4o
    calls_per_month: 10000
```

Resolution order for dynamic model defaults: per-SDK config (`default_models`) >
generic config (`default_model`) > built-in SDK defaults.

You can also pass `--config path/to/.tokentoll.yml` to use a specific config file.

## Token Estimation

By default, tokentoll estimates token counts using a characters/4 heuristic.
For more accurate estimates, install [tiktoken](https://github.com/openai/tiktoken):

```bash
pip install tiktoken
```

When tiktoken is available, tokentoll uses the correct tokenizer encoding for
each model. Unknown models fall back to `cl100k_base`. Tiktoken is lazy-loaded
and encoders are cached, so there is no startup penalty if you don't need it.

## Smart Variable Resolution

Real codebases rarely pass model names as string literals. tokentoll's multi-pass
constant propagation engine follows:

```python
DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o")

class Config:
    model: str = DEFAULT_MODEL

config = Config()
kwargs = {"model": config.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)
# tokentoll resolves: model="gpt-4o", max_tokens=2000
```

- Variable assignments (`MODEL = "gpt-4o"`)
- `os.getenv()` / `os.environ.get()` fallback values
- Function default parameters
- Class attribute defaults
- Constructor argument propagation
- Dict literal and subscript contents
- `**kwargs` unpacking

## Limitations

- Cannot resolve models loaded from external config files or databases at runtime.
  These calls use per-SDK defaults (configurable via `.tokentoll.yml`).
- Token estimates use a characters/4 heuristic unless
  [tiktoken](https://github.com/openai/tiktoken) is installed.
- Monthly estimates assume uniform call volume (configurable via `--calls-per-month`
  or `.tokentoll.yml`).
- Python only for now (JS/TS support planned).

## License

MIT
