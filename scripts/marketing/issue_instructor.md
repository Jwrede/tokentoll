# GitHub Issue for instructor-ai/instructor

## Title

Static analysis found 10 LLM API calls in this repo -- cost breakdown inside

## Body

I built [tokentoll](https://github.com/Jwrede/tokentoll), a static analysis tool that finds LLM API calls in Python code and estimates their cost. I ran it against instructor and wanted to share the results.

### Summary

- **10 LLM API calls** detected (all OpenAI SDK)
- **Estimated total: ~$252/mo** (assuming 1,000 calls/month per call site)

The calls are spread across examples and tests. Since instructor wraps OpenAI calls, tokentoll picks up the underlying `client.chat.completions.create()` patterns.

### What tokentoll does

```bash
pip install tokentoll
tokentoll scan .          # find all LLM calls and their costs
tokentoll diff HEAD~1     # show cost impact of changes
```

Also works as a GitHub Action that comments on PRs with cost impact -- could be useful for catching model changes in examples or defaults.

Not asking for any changes -- just sharing in case it is useful. Happy to answer questions.
