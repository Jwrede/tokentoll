# GitHub Issue for langchain-ai/langchain

## Title

Static analysis found 429 LLM API calls in this repo totaling ~$32,186/mo estimated

## Body

I built [tokentoll](https://github.com/Jwrede/tokentoll), a static analysis tool that finds LLM API calls in Python code and estimates their cost. I ran it against langchain and wanted to share the results.

### Summary

- **429 LLM API calls** detected across the codebase
- **Estimated total: ~$32,186/mo** (assuming 1,000 calls/month per call site)
- Breakdown by SDK: langchain (427), anthropic (1), openai (1)

### Top 10 most expensive call sites

| File | Line | Model | Est. Monthly |
|------|------|-------|-------------|
| `libs/partners/openai/tests/.../test_base.py` | 1073 | o1 | $1,508 |
| `libs/partners/openai/tests/.../test_base.py` | 1091 | o1 | $1,508 |
| `libs/partners/openai/tests/.../test_base.py` | 1326 | o1 | $1,508 |
| `libs/partners/anthropic/tests/.../test_chat_models.py` | 2499 | claude-opus-4-6 | $803 |
| `libs/partners/anthropic/tests/.../test_chat_models.py` | 2981 | claude-opus-4-6 | $803 |
| `libs/partners/anthropic/tests/.../test_chat_models.py` | 139 | claude-opus-4-20250514 | $608 |
| `libs/partners/openai/tests/.../test_base.py` | 159 | o1-preview | $499 |
| `libs/partners/openai/tests/.../test_responses_api.py` | 234 | gpt-5.4 | $481 |
| `libs/partners/openai/tests/.../test_responses_api.py` | 553 | gpt-5.4 | $481 |
| `libs/partners/openai/tests/.../test_responses_api.py` | 1482 | gpt-5.4 | $481 |

The high estimates are mostly from expensive models (o1, claude-opus) in test files. The monthly estimate assumes 1,000 calls/month per call site -- in tests the real volume is much lower, but this highlights which models are the most expensive if the patterns are copied into production code.

### What tokentoll does

tokentoll uses Python's `ast` module to detect LLM API calls, extract model names and parameters, and estimate costs. It detected all 427 LangChain constructor patterns (`ChatOpenAI`, `ChatAnthropic`, `ChatGoogleGenerativeAI`, etc.) plus the raw SDK calls.

```bash
pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1
```

Also works as a GitHub Action that comments on PRs with cost impact.

Not asking for any changes -- just sharing the analysis. Happy to answer questions about the approach.
