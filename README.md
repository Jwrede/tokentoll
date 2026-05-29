# tokentoll

> Prevent LLM cost regressions before production.

[![CI](https://github.com/Jwrede/tokentoll/actions/workflows/ci.yml/badge.svg)](https://github.com/Jwrede/tokentoll/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/tokentoll)](https://pypi.org/project/tokentoll/)
[![GitHub Marketplace](https://img.shields.io/badge/marketplace-tokentoll-blue?logo=github)](https://github.com/marketplace/actions/tokentoll-llm-cost-diff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![tokentoll MCP server](https://glama.ai/mcp/servers/Jwrede/tokentoll/badges/score.svg)](https://glama.ai/mcp/servers/Jwrede/tokentoll)

tokentoll is a CI gate for LLM cost. It statically analyzes Python, JavaScript, and TypeScript for LLM API calls, scores every pull request against a policy you control, and posts a PASS/WARN/FAIL verdict directly on the PR. Optionally, it fails the workflow when the policy is violated, so cost regressions cannot be merged.

<p align="center">
  <img src="demo/demo.gif" alt="tokentoll demo" width="720">
</p>

## Live demo

[Jwrede/tokentoll-demo](https://github.com/Jwrede/tokentoll-demo) is a small polyglot LLM app (Python + TypeScript) wired up to the tokentoll cost gate. Two PRs are already open against it:

- [PR #1: Add Anthropic Haiku translation helper](https://github.com/Jwrede/tokentoll-demo/pull/1). New call site, well within budget. Verdict: PASS, workflow green.
- [PR #2: switch supportbot to gpt-4o](https://github.com/Jwrede/tokentoll-demo/pull/2). A model swap that trips two policy rules. Verdict: FAIL, workflow red.

Open each PR's conversation tab to see the verdict comment tokentoll actually posts.

## The verdict comment

When a PR violates your policy, tokentoll comments with a verdict and a blocking-findings list, then exits non-zero so the check fails. Example:

```md
## tokentoll verdict: FAIL

**Blocking findings (2):**

- `src/agent.py:42` - per-call cost grew 15.0x (threshold 5x)
- total monthly delta +$812.00 exceeds budget $250.00

> Required action: revert the regression, raise the threshold in `.tokentoll.yml`, or add an exemption.
```

When the PR is clean, the verdict is PASS and the comment shows only the cost delta table. When no policy is configured, tokentoll posts an informational delta comment with no verdict.

## Quick start (60 seconds)

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
      - uses: Jwrede/tokentoll@v0.7.0
        with:
          fail-on-policy-violation: true
```

Then add `.tokentoll.yml` to your repo root:

```yaml
budgets:
  max_monthly_delta_usd: 250
  max_callsite_monthly_usd: 100
  max_relative_increase: 5.0

policies:
  block_unknown_models: true
  fail_on_policy_violation: true
```

Future PRs receive a verdict comment. PRs that exceed the thresholds fail the workflow.

For SHA-pinned installs and minimal-permissions setups, see [docs/github-action.md](docs/github-action.md). For the full policy schema, see [docs/policy.md](docs/policy.md). For the security posture, see [docs/security.md](docs/security.md).

## What it detects

**Python**

| SDK | Patterns |
|-----|----------|
| OpenAI | `chat.completions.create`, `responses.create` |
| Anthropic | `messages.create`, `messages.stream` |
| Google GenAI | `models.generate_content` |
| LiteLLM | `completion`, `acompletion` |
| LangChain | `ChatOpenAI`, `ChatAnthropic`, `init_chat_model` |
| Zhipu AI | `ZhipuAiClient`, `ZhipuAI` (GLM models) |

**JavaScript / TypeScript** (parsed via tree-sitter, handles `.js`, `.jsx`, `.ts`, `.tsx`)

| SDK | Patterns |
|-----|----------|
| OpenAI Node SDK | `client.chat.completions.create`, `client.responses.create`, `client.embeddings.create` |
| Anthropic SDK | `client.messages.create`, `client.messages.stream` |
| Vercel AI SDK | `generateText`, `streamText`, `generateObject`, `streamObject`, `embed`, `embedMany` |
| LangChain.js | `new ChatOpenAI`, `new ChatAnthropic`, `new ChatGoogleGenerativeAI`, ... |
| OpenAI-compatible | same shape as OpenAI Node SDK, picked up automatically |

## Policy rules

The policy block in `.tokentoll.yml` controls when a PR fails:

| Rule | Trigger |
|------|---------|
| `budgets.max_monthly_delta_usd` | total estimated monthly delta exceeds the threshold |
| `budgets.max_callsite_monthly_usd` | any new or changed call site exceeds the threshold |
| `budgets.max_relative_increase` | per-call cost for any modified call site grows by more than this multiplier |
| `policies.block_unknown_models` | any new or modified call site uses an unpriced or unresolved model |
| `policies.fail_on_policy_violation` | `tokentoll diff` exits 1 on FAIL (CI gate behavior) |

Each rule is independent. Leave a field unset to disable that rule. Full reference in [docs/policy.md](docs/policy.md).

## CLI

```bash
pip install tokentoll

# Scan current directory for LLM API calls and their costs
tokentoll scan .

# Show cost impact of your last commit
tokentoll diff HEAD~1

# Compare two refs and fail on policy violation
tokentoll diff main..HEAD --fail-on-policy-violation
```

Subcommands:

```
tokentoll scan [PATH...] [--format table|json|markdown] [--calls-per-month N] [--config PATH]
tokentoll diff [REF] [--base REF] [--head REF] [--format table|json|markdown|github-comment]
               [--config PATH] [--fail-on-policy-violation]
tokentoll update    # refresh bundled pricing data from LiteLLM
```

## Configuration

`.tokentoll.yml` lives in the repo root and is auto-discovered. Beyond the policy block:

```yaml
# Per-SDK defaults for dynamic (runtime-resolved) model names
default_models:
  openai: gpt-4o-mini
  anthropic: claude-haiku-3-20240307

# Assumed monthly call volume per call site (used for dollar estimates)
calls_per_month: 5000

# Skip cost estimation for dynamic models entirely.
# Default false: dynamic calls are priced against the per-SDK default.
skip_dynamic_models: false

# Default excludes (tests/, examples/, docs/, cookbook/, benchmarks/, evals/,
# scripts/, notebooks/) are applied automatically. Opt out with:
use_default_excludes: false

# Additional excludes (prefix or glob)
exclude:
  - "*_test.py"
  - vendor/

# Per-path overrides (longest prefix match)
overrides:
  - path: src/agents/
    default_model: gpt-4o
    calls_per_month: 10000
  - path: src/azure/
    skip_dynamic_models: true
```

Resolution order for dynamic model defaults: `default_models` (per-SDK) > `default_model` (generic) > built-in SDK defaults.

## Security

tokentoll requires no API keys, sends no telemetry, and runs entirely inside your CI environment. Pricing data ships with the package and updates from LiteLLM on demand. For the recommended permission set, SHA pinning, and fork PR risk, see [docs/security.md](docs/security.md).

## MCP server

[![tokentoll MCP server](https://glama.ai/mcp/servers/Jwrede/tokentoll/badges/card.svg)](https://glama.ai/mcp/servers/Jwrede/tokentoll)

tokentoll ships an MCP (Model Context Protocol) server so Claude Code and other MCP hosts can check the cost impact of LLM code changes from inside an agent conversation:

```bash
pip install tokentoll[mcp]
claude mcp add --transport stdio tokentoll -- tokentoll-mcp
```

Two tools are exposed: `scan` (estimate costs across a path) and `diff` (compare two refs). Both return JSON.

## How it works

```
  Source code (.py, .ts, .tsx, .js, .jsx)
        |
        v
  +----------------+   +------------------+
  | AST scanners   |-->| SDK detectors    |
  | ast (Python) + |   | OpenAI, Anthropic|
  | tree-sitter    |   | Google, LiteLLM, |
  | (JS/TS)        |   | LangChain, Zhipu,|
  +----------------+   | Vercel AI SDK    |
                       +------------------+
                              |
                              v
                       +------------------+
                       | Pricing engine   |
                       | 2200+ models     |
                       +------------------+
                              |
                              v
                       +------------------+
                       | Diff engine      |
                       | (old vs new)     |
                       +------------------+
                              |
                              v
                       +------------------+
                       | Policy evaluator |
                       | PASS/WARN/FAIL   |
                       +------------------+
                              |
                              v
                       +------------------+
                       | PR comment / CLI |
                       | output           |
                       +------------------+
```

A multi-pass constant propagation engine resolves model names through variable assignments, `os.getenv()` / `process.env.X` fallbacks, function defaults, class attributes, constructor arguments, dict and object literals, `**kwargs` unpacking, and Vercel AI SDK provider wrappers (`openai("gpt-4o")`), so real-world code with indirection still produces useful estimates.

## Pricing data

Pricing is bundled and works offline. To refresh from LiteLLM:

```bash
tokentoll update
```

Coverage: 300+ models across OpenAI, Anthropic, Google, AWS Bedrock, Azure, and more, plus 2200+ entries from LiteLLM's combined catalog.

## Limitations

- Static analysis only. Models loaded from databases or remote config cannot be resolved; tokentoll falls back to the configured per-SDK default and marks the call site as `(default)`.
- Token estimates use a characters/4 heuristic unless [tiktoken](https://github.com/openai/tiktoken) is installed (`pip install tokentoll[tiktoken]`).
- Monthly estimates assume uniform call volume per call site. Override per-project with `calls_per_month` or per-path with `overrides`.
- JS/TS resolution is same-file only. Importing a model name from another module produces a dynamic call site rather than a resolved value.

## Roadmap

- **v0.9**: Public demo repo with a known-failing PR, gpt-researcher case study, expanded adoption section
- **Future**: Context-aware call frequency inference (FastAPI routes versus scripts versus loops); cross-file import resolution for JS/TS

## License

MIT
