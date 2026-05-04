# r/Python Post

## Title

I built a zero-dependency CLI that finds LLM API calls in your Python code and estimates costs

## Body

**tokentoll** uses Python's `ast` module to statically analyze your codebase for
LLM API calls (OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Zhipu/GLM) and
estimates their cost using real pricing data.

```
pip install tokentoll
tokentoll scan .          # find all LLM calls and their costs
tokentoll diff HEAD~1     # show cost impact of your last commit
```

![demo](https://raw.githubusercontent.com/Jwrede/tokentoll/main/demo/demo.gif)

Some details on the implementation:

- Uses `ast.parse()` and `ast.walk()` to find call patterns like
  `client.chat.completions.create(model="gpt-4o", ...)`
- Tracks variable assignments to resolve client names
  (e.g., `client = OpenAI()` then `client.chat...`)
- Multi-pass constant propagation resolves model names through variables,
  `os.getenv()` fallbacks, class attributes, `**kwargs`, and constructor args
- Tiered model name resolution handles provider prefixes, region prefixes,
  and date suffixes
- Per-SDK defaults for dynamic model names (Anthropic calls default to
  claude-sonnet pricing, Google calls to gemini-flash, etc.)
- Configurable via `.tokentoll.yml` with per-path overrides
- Optional tiktoken integration for accurate token counting
- Pricing data from LiteLLM (2200+ models), auto-cached locally
- Zero runtime dependencies (stdlib only: ast, json, subprocess, argparse)

Also works as a GitHub Action that comments on PRs with cost impact.

GitHub: https://github.com/Jwrede/tokentoll

Happy to answer questions about the AST parsing approach.
