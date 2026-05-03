# Show HN: tokentoll -- Catch LLM cost changes in code review

## Title (for HN submit box)

Show HN: tokentoll -- Catch LLM API cost changes in code review

## Body

A model swap from gpt-4o-mini to gpt-4o costs 15x more. A new API call in a
hot path can add $10k/month. These changes hide in normal code review.

tokentoll is a CLI tool (and GitHub Action) that statically analyzes your Python
code for LLM API calls, estimates their cost using real pricing data, and shows
you the cost impact of every change.

    pip install tokentoll
    tokentoll scan .          # find all LLM calls and their costs
    tokentoll diff HEAD~1     # show cost impact of last commit

It uses Python's ast module to detect calls to OpenAI, Anthropic, Google GenAI,
LiteLLM, and LangChain SDKs. Pricing data is sourced from LiteLLM's pricing
database (2200+ models) and cached locally.

Zero runtime dependencies. Works offline with bundled pricing data.

Think Infracost, but for LLM API spend instead of cloud infrastructure.

https://github.com/Jwrede/tokentoll

## Posting notes

- Post on Tuesday or Wednesday around 9am ET
- Keep it factual, no hype
- Respond to every comment within an hour
