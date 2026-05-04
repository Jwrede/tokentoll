# r/mlops Post

## Title

I built a CLI that catches LLM API cost changes in code review (like Infracost for Terraform)

## Body

I kept running into the same problem: someone swaps a model in a PR, the code
review looks fine, and then the LLM bill spikes. A gpt-4o-mini to gpt-4o swap
is a 15x cost increase that's invisible in a diff.

So I built **tokentoll**, a CLI tool that statically analyzes Python code for
LLM API calls and shows you the cost impact of changes.

```
pip install tokentoll
tokentoll scan .          # show all LLM calls and estimated costs
tokentoll diff HEAD~1     # show cost impact of last commit
```

![demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

It detects calls to OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, and
Zhipu (GLM) SDKs using Python's ast module. Pricing data comes from LiteLLM's database
(2200+ models) and is cached locally.

When model names are dynamic (loaded from env vars or config), it applies
per-SDK defaults (Anthropic calls get claude-sonnet pricing, Google calls
get gemini-flash, etc.) so you still see useful estimates. Everything is
configurable via a `.tokentoll.yml` file.

Also works as a GitHub Action that posts cost diffs as PR comments.

Zero runtime dependencies. MIT licensed.

GitHub: https://github.com/Jwrede/tokentoll

Would love feedback, especially on what SDK patterns I'm missing or edge
cases you'd want handled.
