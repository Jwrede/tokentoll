# r/Python Post

## Title

I built a zero-dependency CLI that finds LLM API calls in your Python code and estimates costs

## Body

**tokentoll** uses Python's `ast` module to statically analyze your codebase for
LLM API calls (OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain) and
estimates their cost using real pricing data.

```
pip install tokentoll
tokentoll scan .          # find all LLM calls and their costs
tokentoll diff HEAD~1     # show cost impact of your last commit
```

Some details on the implementation:

- Uses `ast.parse()` and `ast.walk()` to find call patterns like
  `client.chat.completions.create(model="gpt-4o", ...)`
- Tracks variable assignments to resolve client names
  (e.g., `client = OpenAI()` then `client.chat...`)
- Tiered model name resolution handles provider prefixes, region prefixes,
  and date suffixes
- Pricing data from LiteLLM (2200+ models), auto-cached locally
- Zero runtime dependencies -- stdlib only (ast, json, subprocess, argparse)

I tested it against real codebases: found 1,387 calls in LiteLLM, 429 in
LangChain, and 10 in instructor. 1,834 total calls detected, zero crashes.

Also works as a GitHub Action that comments on PRs with cost impact.

GitHub: https://github.com/Jwrede/tokentoll

Happy to answer questions about the AST parsing approach.
