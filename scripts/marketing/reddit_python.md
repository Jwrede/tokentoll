# r/Python Post

## Title

tokentoll: a CI gate that catches LLM API cost regressions in Python (and JS/TS) before they merge

## Body

A model swap from `gpt-4o-mini` to `gpt-4o` is roughly 15x more expensive per token. In a normal code diff it looks like a one-word change, indistinguishable from a typo fix. Tests pass, reviewer approves, the cost shows up on next month's invoice.

I wrote **tokentoll** to catch this in code review. It is a CLI plus GitHub Action that statically analyzes Python (and JS/TS via tree-sitter) for LLM SDK calls, prices them against a 2200+ model catalog from LiteLLM, and posts a PASS/WARN/FAIL verdict on the PR against a policy you control.

Python coverage: OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu.

```
$ tokentoll diff main..HEAD

~ MODIFIED src/agents/summarizer.py:42
  openai | Model: gpt-4o-mini -> gpt-4o
  Monthly: +$26.20 per call site (15x increase)

+ ADDED src/agents/rewriter.py:35
  openai | Model: gpt-4o
  Monthly: +$26.50

## tokentoll verdict: FAIL
per-call cost grew 15.0x (threshold 5x)
```

The part I'm most proud of technically is the multi-pass constant propagation in the Python scanner. Production codebases rarely write `model="gpt-4o"` as a literal. They pass model names through env vars, class attributes, dict unpacking, kwargs, and constructor arguments. tokentoll iterates until a fixed point and resolves through all of those:

```python
DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o-mini")

class Config:
    model: str = DEFAULT_MODEL

cfg = Config()
kwargs = {"model": cfg.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)
# resolved: model="gpt-4o-mini", max_tokens=2000
```

What it does not do.

- Resolve models loaded from a database or remote config (those fall back to a per-SDK default and get flagged).
- Predict actual call volume. You configure `calls_per_month` per project or per path.
- Cross-module import resolution in JS/TS (Python is fine).

Adoption proof so far: merged into [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) (27k stars). v0.8.3 (shipped today) fixes a diff-matching bug I caught while validating against their open PR queue: shifted call sites were getting double-counted as REMOVED + ADDED pairs.

Install:

    pip install tokentoll
    tokentoll scan .
    tokentoll diff main..HEAD

GitHub: https://github.com/Jwrede/tokentoll

Curious what false positives or SDK patterns it breaks on in your codebase.

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one FIRST (biggest audience, ~1.3M members)
- Respond to every comment in the first hour
- Accept criticism gracefully, be honest about limitations
