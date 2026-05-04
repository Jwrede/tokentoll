# Show HN: tokentoll - Catch LLM cost changes in code review

## Title (for HN submit box)

Show HN: tokentoll - Catch LLM API cost changes in code review

## URL

https://github.com/Jwrede/tokentoll

## Body (optional, only if posting as text instead of link)

A model swap from gpt-4o-mini to gpt-4o costs 15x more. A new API call in a
hot path can add $10k/month. These changes hide in normal code review.

tokentoll is a CLI tool (and GitHub Action) that statically analyzes your Python
code for LLM API calls, estimates their cost, and shows you the cost impact of
every change.

    pip install tokentoll
    tokentoll scan .          # find all LLM calls and their costs
    tokentoll diff HEAD~1     # show cost impact of last commit

It uses Python's ast module to detect calls to OpenAI, Anthropic, Google GenAI,
LiteLLM, LangChain, and Zhipu (GLM) SDKs. A multi-pass constant propagation engine follows
variable assignments, class attributes, **kwargs, os.getenv() fallbacks, and
constructor arguments to resolve model names that aren't string literals.

When a model name is truly dynamic (loaded from a database, external config),
tokentoll applies sensible per-SDK defaults (e.g. Anthropic calls use
claude-sonnet pricing, Google calls use gemini-flash) so you still get useful
estimates. These defaults are configurable via a .tokentoll.yml file.

Pricing data is sourced from LiteLLM's database (2200+ models). Zero runtime
dependencies. Works offline with bundled pricing data.

Think Infracost, but for LLM API spend instead of cloud infrastructure.

https://github.com/Jwrede/tokentoll

## Posting notes

- Post on Tuesday or Wednesday around 9am ET
- Keep it factual, no hype
- Respond to every comment within an hour
