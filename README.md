# tokentoll

> Catch LLM cost changes in code review. Infracost for LLM spend.

A CLI tool and GitHub Action that statically analyzes your code for LLM API calls,
estimates their cost, and shows you the cost impact of every change -- in your
terminal or as a PR comment.

## The Problem

A single model swap from `gpt-4o-mini` to `gpt-4o` increases costs **15x**.
A new API call in a hot path can add **$10,000/month** to your bill.
These changes hide in normal code review.

tokentoll finds LLM API calls in your code, estimates their cost,
and shows you the cost impact of every change -- before it hits production.

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

      - uses: Jwrede/tokentoll@v1
        with:
          calls-per-month: "5000"
```

## What It Detects

| SDK | Patterns | Status |
|-----|----------|--------|
| OpenAI | `chat.completions.create`, `responses.create` | Supported |
| Anthropic | `messages.create`, `messages.stream` | Supported |
| Google GenAI | `models.generate_content` | Supported |
| LiteLLM | `completion`, `acompletion` | Supported |
| LangChain | `ChatOpenAI`, `ChatAnthropic`, `init_chat_model` | Supported |
| JS/TS SDKs | -- | Planned |

## How It Works

1. Parses Python files using the `ast` module to find LLM API calls
2. Extracts model name, max_tokens, and prompt content where possible
3. Looks up pricing from a bundled database (sourced from LiteLLM, 300+ models)
4. For diff mode: compares calls between two git refs and computes the cost delta
5. Outputs a cost report as a table, JSON, or GitHub PR comment

## CLI Reference

```
tokentoll scan [PATH...] [--format table|json|markdown] [--calls-per-month N]
tokentoll diff [REF] [--base REF] [--head REF] [--format table|json|markdown|github-comment]
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

## Limitations

- Static analysis only -- cannot estimate costs for dynamic model names
  or computed prompts (these are flagged but not priced)
- Token estimates use a character/4 heuristic unless tiktoken is installed
- Monthly estimates assume uniform call volume (configurable via `--calls-per-month`)
- Python only for now (JS/TS support planned)

## License

MIT
