# LinkedIn Post

A single model swap from gpt-4o-mini to gpt-4o increases LLM API costs by 15x.
These changes are invisible in normal code review.

I built tokentoll -- an open-source CLI tool and GitHub Action that statically
analyzes Python code for LLM API calls and shows the cost impact of every
change before it hits production.

How it works:
- Parses Python source code using the ast module
- Detects calls to OpenAI, Anthropic, Google GenAI, LiteLLM, and LangChain
- Looks up real pricing data (2200+ models)
- Shows cost delta per commit or PR

Think Infracost, but for LLM API spend.

Validated against real open-source projects: found 1,387 LLM calls in LiteLLM,
429 in LangChain, 1,834 total across 5 repos. Zero crashes.

Zero runtime dependencies. MIT licensed. Works as a GitHub Action with
automatic PR comments.

pip install tokentoll
tokentoll scan .
tokentoll diff HEAD~1

GitHub: https://github.com/Jwrede/tokentoll

#OpenSource #LLM #MLOps #DevTools #AI #MachineLearning #Python
