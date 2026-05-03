# X/Twitter Launch Thread

## Tweet 1 (hook)

A model swap from gpt-4o-mini to gpt-4o costs 15x more.

These changes hide in normal code review.

I built tokentoll -- a CLI that catches LLM cost changes before they ship.

pip install tokentoll
tokentoll diff HEAD~1

Zero dependencies. 2200+ models. Works offline.

github.com/Jwrede/tokentoll

## Tweet 2 (demo)

How it works:

1. Parses your Python with ast module
2. Multi-pass constant propagation resolves model names through variables, **kwargs, class attrs
3. Detects OpenAI, Anthropic, Google, LiteLLM, LangChain calls
4. Looks up real pricing (2200+ models, auto-cached)
5. Shows you the cost delta

[ATTACH: terminal screenshot of tokentoll diff output]

## Tweet 3 (GitHub Action angle)

It also works as a GitHub Action.

Every PR gets a comment showing the cost impact of LLM API changes.

Model swap? New API call? Removed endpoint? You see the dollar impact before merging.

[ATTACH: screenshot of PR comment]

## Tweet 4 (CTA)

If you're building with LLM APIs, give it a try:

pip install tokentoll
tokentoll scan .

Star it if it's useful: github.com/Jwrede/tokentoll

Built with zero runtime dependencies, MIT licensed.
