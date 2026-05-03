# r/devops Post

## Title

GitHub Action that comments on PRs with LLM API cost impact (like Infracost for Terraform)

## Body

If your team uses LLM APIs (OpenAI, Anthropic, etc.), you've probably had
surprise cost spikes from model swaps or new API calls that slipped through
code review.

I built **tokentoll** -- a GitHub Action (and CLI) that statically analyzes
Python code for LLM API calls, estimates their cost, and posts the delta as a
PR comment.

```yaml
- uses: Jwrede/tokentoll@v1
  with:
    calls-per-month: "5000"
```

It detects model swaps (gpt-4o-mini -> gpt-4o = 15x cost increase), new API
calls, and removed endpoints. The PR comment shows a table with per-call cost
and monthly impact.

Same concept as Infracost for Terraform, but for LLM API spend.

- Pricing data from LiteLLM (2200+ models), auto-cached
- Supports OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain
- Zero runtime dependencies
- MIT licensed

GitHub: https://github.com/Jwrede/tokentoll
