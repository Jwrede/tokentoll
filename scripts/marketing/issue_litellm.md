# GitHub Issue for BerriAI/litellm

## Title

Your repo has 1,387 LLM API calls totaling ~$22,858/mo estimated -- here is the full breakdown

## Body

I built [tokentoll](https://github.com/Jwrede/tokentoll), a static analysis tool that finds LLM API calls in Python code and estimates their cost using real pricing data. I ran it against litellm as a stress test and wanted to share the results.

### Summary

- **1,387 LLM API calls** detected across the codebase
- **Estimated total: ~$22,858/mo** (assuming 1,000 calls/month per call site)
- Breakdown by SDK: litellm (1,343), openai (42), anthropic (1), langchain (1)

### Top 10 most expensive call sites

| File | Line | Model | Est. Monthly |
|------|------|-------|-------------|
| `tests/llm_translation/test_openai.py` | 622 | o3-deep-research-2025-06-26 | $1,000 |
| `tests/llm_translation/test_azure_o_series.py` | 168 | azure/o1-preview | $492 |
| `tests/llm_translation/test_databricks.py` | 980 | databricks/databricks-claude-3-7-sonnet | $482 |
| `tests/llm_translation/test_databricks.py` | 1043 | databricks/databricks-claude-3-7-sonnet | $482 |
| `tests/llm_translation/test_databricks.py` | 1238 | databricks/databricks-claude-3-7-sonnet | $482 |
| `tests/llm_translation/test_databricks.py` | 1285 | databricks/databricks-claude-3-7-sonnet | $482 |
| `tests/llm_translation/test_databricks.py` | 1339 | databricks/databricks-claude-3-7-sonnet | $482 |
| `tests/test_litellm/test_main.py` | 769 | gpt-5.4 | $480 |
| `tests/llm_translation/test_openrouter.py` | 13 | openrouter/anthropic/claude-3.7-sonnet | $480 |
| `cookbook/litellm_proxy_server/mcp/mcp_with_litellm_proxy.py` | 15 | gpt-5 | $321 |

Most of these are in test files (expected for litellm), but the cookbook examples and proxy config files represent real usage patterns that could surprise users.

### What tokentoll does

tokentoll uses Python's `ast` module to statically detect LLM API calls, extract model names and token parameters, and estimate costs using your own pricing database. It also has a `diff` command that shows cost impact between git refs -- useful for catching model swaps in PRs.

```bash
pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1
```

The litellm scan was a great stress test -- 1,387 calls with zero crashes. It also helped me improve model name resolution for provider prefixes (databricks/, openrouter/, azure/) and region prefixes.

Not asking for any changes here -- just sharing the analysis in case it is useful. Happy to answer any questions about the methodology.
