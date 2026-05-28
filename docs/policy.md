# Policy reference

tokentoll's policy lives in `.tokentoll.yml` at the repo root. The file is discovered by walking up from the path being scanned, so it works from anywhere in the repo. The policy is evaluated by `tokentoll diff` (and through it, by the GitHub Action) and produces a verdict of PASS, WARN, or FAIL.

Each rule is independent. Leave a field unset to disable that rule. An empty policy always produces PASS with no banner.

## Schema

```yaml
budgets:
  max_monthly_delta_usd: 250         # float, USD
  max_callsite_monthly_usd: 100      # float, USD
  max_relative_increase: 5.0          # float, multiplier (x)

policies:
  block_unknown_models: true          # bool
  fail_on_policy_violation: true     # bool
```

## Rules

### `budgets.max_monthly_delta_usd`

Triggers FAIL when the sum of monthly cost deltas across all changed call sites exceeds the threshold. This is the simplest "total spend impact" cap.

Inputs to the calculation:
- Each modified, added, or removed call site contributes its monthly delta.
- The default monthly call volume is 1000 calls per call site, configurable globally with `calls_per_month` or per-path with `overrides`.

Example finding:
```
total monthly delta +$812.00 exceeds budget $250.00
```

### `budgets.max_callsite_monthly_usd`

Triggers FAIL for any single added or modified call site whose monthly delta exceeds the threshold. Catches "one new expensive call site" cases that a generous total budget would miss.

Removed call sites are not evaluated.

Example finding:
```
src/rag.py:88 - call site adds $480.00/mo (threshold $100.00/mo)
```

### `budgets.max_relative_increase`

Triggers FAIL when a modified call site's per-call cost grows by more than this multiplier. Useful for catching model swaps like `gpt-4o-mini` to `gpt-4o` (about 15x) without tying the rule to absolute dollar amounts.

Only evaluated for MODIFIED call sites where both old and new estimates have a positive per-call cost. Added and removed call sites do not contribute.

Example finding:
```
src/agent.py:42 - per-call cost grew 15.0x (threshold 5x)
```

### `policies.block_unknown_models`

Triggers FAIL when an added or modified call site uses a model that cannot be priced. This includes:
- Models not in tokentoll's pricing database
- Models resolved to a per-SDK default with `skip_dynamic_models: true` set

Use this to require explicit, priceable model names on every call site, which forces config updates rather than silent fallback.

Example finding:
```
src/llm.py:12 - unknown or unpriced model `internal-llama`
```

### `policies.fail_on_policy_violation`

When `true`, `tokentoll diff` exits with status 1 whenever the verdict is FAIL. This is what turns tokentoll from a reporter into a CI gate. The CLI flag `--fail-on-policy-violation` has the same effect and is what the GitHub Action's `fail-on-policy-violation` input toggles.

Both signals are OR'd: setting either is enough to fail.

## Full example

```yaml
# Production app with a tight cost gate
budgets:
  max_monthly_delta_usd: 250
  max_callsite_monthly_usd: 100
  max_relative_increase: 5.0

policies:
  block_unknown_models: true
  fail_on_policy_violation: true

# Surface area where the policy applies
calls_per_month: 5000
skip_dynamic_models: false

# Stricter rules for the hot path
overrides:
  - path: src/agents/hotpath/
    calls_per_month: 50000
```

## Verdict surfacing

The verdict appears in three places:

1. **PR comment** (when running via GitHub Action). Leads with `## tokentoll verdict: FAIL`, then a blocking-findings list, then the cost delta table.
2. **CLI output** (any format). Markdown prepends the banner; table prefixes a `tokentoll verdict: FAIL` header; JSON adds a top-level `verdict` object.
3. **Exit code**. 1 when FAIL and `fail_on_policy_violation` (or the CLI flag) is set; 0 otherwise.

## What the verdict does not check

- It does not verify production traffic. The monthly figure is built from `calls_per_month` assumptions, not telemetry.
- It does not run the code. Models constructed entirely at runtime (loaded from a database, a remote config service) cannot be priced.
- It does not catch streaming-token blowups or prompt-length regressions. Output cost uses `max_tokens` if statically known; input cost uses a 500-token default unless prompt content is statically analyzable.

For these, complement tokentoll with runtime observability.
