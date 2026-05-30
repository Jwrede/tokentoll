# X/Twitter Launch Thread

## Tweet 1 (hook + demo)

A one-word swap from gpt-4o-mini to gpt-4o is about 15x more expensive per token.

It looks like a typo fix in a diff. Tests pass. Linter is happy. Reviewer approves.

Then the bill spikes.

tokentoll is a CI gate that catches this in PR review.

pip install tokentoll
github.com/Jwrede/tokentoll

[ATTACH: demo/demo.gif]

## Tweet 2 (demo output, reply to tweet 1)

Example diff against main:

$ tokentoll diff main..HEAD

~ MODIFIED src/agents/summarizer.py:42
  openai | gpt-4o-mini to gpt-4o
  Monthly: +$26.20 (15x increase)

## tokentoll verdict: FAIL
per-call cost grew 15.0x (threshold 5x)

Configurable per-repo via .tokentoll.yml.

## Tweet 3 (how it works, reply to tweet 2)

How it works.

Python via the ast module. JS and TS via tree-sitter. Multi-pass constant propagation resolves model names through variables, env vars, class attributes, kwargs, and Vercel AI SDK provider wrappers like openai("gpt-4o").

2200+ models priced from LiteLLM, bundled.

## Tweet 4 (adoption + CTA, reply to tweet 3)

Just merged into assafelovic/gpt-researcher (27k stars).

One line of YAML as a GitHub Action:

  uses: Jwrede/tokentoll@v0.8.3
  with:
    fail-on-policy-violation: true

Detects OpenAI, Anthropic, Google, LiteLLM, LangChain, Zhipu, plus the OpenAI Node SDK, Anthropic SDK, Vercel AI SDK, LangChain.js.

Star if useful: github.com/Jwrede/tokentoll

What SDK patterns am I missing?
