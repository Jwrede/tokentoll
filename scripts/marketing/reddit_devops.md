# r/devops Post

## Title

GitHub Action that blocks PRs on LLM API cost regressions (like Infracost for Terraform, but for model calls)

## Body

If your team is shipping LLM features, the cost regression vector that is hardest to see in code review is a one-word model swap. `gpt-4o-mini` to `gpt-4o` is about 15x more expensive per token. It looks like a typo fix in a diff. Tests pass, CI is green, the bill spikes next month.

**tokentoll** is a GitHub Action that adds a real gate. It parses Python (ast), JavaScript, and TypeScript (tree-sitter) for LLM SDK calls, prices them against a bundled 2200+ model catalog, and posts a PASS/WARN/FAIL verdict on the PR. With `fail-on-policy-violation: true`, a FAIL exits non-zero so the check goes red and blocks the merge.

Minimal workflow:

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

Policy at `.tokentoll.yml` in the repo root:

```yaml
budgets:
  max_monthly_delta_usd: 250
  max_callsite_monthly_usd: 100
  max_relative_increase: 5.0

policies:
  block_unknown_models: true
  fail_on_policy_violation: true
```

The PR comment when a budget is blown:

```
## tokentoll verdict: FAIL

Blocking findings (2):

- src/agent.py:42 per-call cost grew 15.0x (threshold 5x)
- total monthly delta +$812.00 exceeds budget $250.00

Required action: revert the regression, raise the threshold, or add an exemption.
```

Security posture. No API keys required, no telemetry, pricing data ships in the package, runs entirely inside your CI environment. The action supports SHA pinning for supply-chain hygiene; the README lists the recommended pin.

Adoption so far: merged into `assafelovic/gpt-researcher` (27k stars) and a few smaller AI apps. Source: https://github.com/Jwrede/tokentoll

How is your team handling LLM cost visibility in pipelines today? Genuinely curious.

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one SECOND (medium audience, ~350K)
- At least 24 hours after r/Python post
- Frame as infrastructure/guardrail, not a Python library
