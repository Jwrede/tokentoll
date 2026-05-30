# X/Twitter Launch Thread

## Tweet 1 (hook + demo)

A model swap from gpt-4o-mini to gpt-4o costs 15x more.

It looks like a one-word diff. Tests pass. Linter is happy. Reviewer approves.

Then the bill spikes.

I built tokentoll to catch this before it ships:

$ tokentoll diff HEAD~1

~ MODIFIED src/agents/summarizer.py:42
  openai | Model: gpt-4o-mini -> gpt-4o
  Monthly: +$26.20 (15x increase)

pip install tokentoll

github.com/Jwrede/tokentoll

[ATTACH: demo/demo.gif]

## Tweet 2 (technical angle, reply to tweet 1)

How it works:

tokentoll uses Python's ast module to find LLM API calls and resolve model names through variables, **kwargs, os.getenv() fallbacks, class attributes, and constructor args.

Pricing for 2200+ models. Zero runtime dependencies. Stdlib only.

It catches what code review misses: the dollar sign.

## Tweet 3 (GitHub Action angle, reply to tweet 2)

It also works as a GitHub Action. One line of YAML:

- uses: Jwrede/tokentoll@v0.8.3

Every PR gets a PASS/WARN/FAIL verdict against a policy you define: max monthly delta, max relative increase, block unknown models.

Like Infracost for Terraform, but for LLM API spend.

## Tweet 4 (adoption + CTA, reply to tweet 3)

Just merged into assafelovic/gpt-researcher (27k stars).

Detects: OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu in Python. Plus OpenAI Node SDK, Anthropic SDK, Vercel AI SDK, LangChain.js in JS and TS via tree-sitter.

Star if useful: github.com/Jwrede/tokentoll

What SDK patterns am I missing?
