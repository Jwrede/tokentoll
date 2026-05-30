# r/Python Post

## Title

I built a zero-dep CLI that finds every LLM API call in your Python code and estimates what it costs

## Body

Last month I was reviewing a PR where someone swapped `gpt-4o-mini` for `gpt-4o`. The tests passed, the types checked out, I approved it. Our bill went from $800/month to $12,000/month. One parameter change, invisible in a diff.

I looked for a tool that could catch this. Infracost does it for Terraform, but nothing exists for LLM API calls. So I built one.

**tokentoll** parses your Python with `ast` (and your JS/TS with tree-sitter), finds calls to OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu, Vercel AI SDK, and LangChain.js, and looks up real pricing for 2200+ models. Just merged into [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) (27k stars).

```
$ pip install tokentoll
$ tokentoll diff HEAD~1

~ MODIFIED src/agents/summarizer.py:42
  openai | Model: gpt-4o-mini -> gpt-4o
  Monthly: +$26.20 per call site (15x increase)

+ ADDED src/agents/rewriter.py:35
  openai | Model: gpt-4o
  Monthly: +$26.50
```

The part I'm most proud of technically is the multi-pass constant propagation. Real codebases don't write `model="gpt-4o"` as a literal. They pass it through env vars, class attributes, `**kwargs`, constructor args. tokentoll resolves these:

```python
DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o")

class Config:
    model: str = DEFAULT_MODEL

config = Config()
kwargs = {"model": config.model, "max_tokens": 2000}
client.chat.completions.create(**kwargs)
# tokentoll resolves: model="gpt-4o", max_tokens=2000
```

Also works as a GitHub Action that comments on PRs with cost impact. You can exclude paths (tests/, examples/) and configure per-path call volume via `.tokentoll.yml`.

Zero runtime dependencies. Stdlib only: ast, json, subprocess, argparse. Optional tiktoken for better token estimates.

GitHub: https://github.com/Jwrede/tokentoll

Curious what it finds in your codebase. What patterns am I missing?

## Posting notes

- Post Tuesday-Thursday, 6-10 AM US Eastern
- Post this one FIRST (biggest audience, ~1.3M members)
- Respond to every comment in the first hour
- Accept criticism gracefully, be honest about limitations
