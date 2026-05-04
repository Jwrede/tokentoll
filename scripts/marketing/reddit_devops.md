# r/devops Post

## Title

GitHub Action that comments on PRs with LLM API cost impact (like Infracost for Terraform)

## Body

If your team uses LLM APIs (OpenAI, Anthropic, etc.), you've probably had
surprise cost spikes from model swaps or new API calls that slipped through
code review.

I built **tokentoll**, a GitHub Action (and CLI) that statically analyzes
Python code for LLM API calls, estimates their cost, and posts the delta as a
PR comment.

```yaml
- uses: Jwrede/tokentoll@v0.5.2
```

![demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

It detects model swaps (gpt-4o-mini -> gpt-4o = 15x cost increase), new API
calls, and removed endpoints. The PR comment shows a table with per-call cost
and monthly impact.

When model names are dynamic (loaded from env vars or config at runtime),
it applies per-SDK defaults so you still get useful estimates. Anthropic calls
get claude-sonnet pricing, Google calls get gemini-flash, and so on.

Same concept as Infracost for Terraform, but for LLM API spend.

- Pricing data from LiteLLM (2200+ models), auto-cached
- Supports OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain
- Configurable via `.tokentoll.yml` (per-path overrides, custom defaults)
- Zero runtime dependencies
- MIT licensed

GitHub: https://github.com/Jwrede/tokentoll
