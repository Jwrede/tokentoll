# Show HN: Tokentoll - Static analysis that catches LLM cost changes in code review

## Title (for HN submit box)

Show HN: Tokentoll - Static analysis that catches LLM cost changes in code review

## URL

https://github.com/Jwrede/tokentoll

## First comment (post immediately after submitting)

I kept finding model swaps in PRs that looked harmless but caused cost spikes.
A gpt-4o-mini to gpt-4o change is 15x more expensive per token, and it's
invisible in a normal diff.

tokentoll statically analyzes Python, JavaScript, and TypeScript for LLM API
calls (OpenAI, Anthropic, Google GenAI, LiteLLM, LangChain, Vercel AI SDK,
Zhipu), resolves model names through variable assignments, **kwargs,
os.getenv()/process.env fallbacks, and looks up real pricing for 2200+ models.
The interesting technical bit is the multi-pass constant propagation that
follows model names through class attributes, constructor args, dict unpacking,
and Vercel AI SDK provider wrappers.

Example:

    $ tokentoll diff HEAD~1

    ~ MODIFIED src/agents/summarizer.py:42
      openai | Model: gpt-4o-mini -> gpt-4o
      Monthly: +$26.20 (15x increase)

Also works as a GitHub Action that comments PASS/WARN/FAIL on PRs against a
policy you define (max_monthly_delta_usd, max_relative_increase,
block_unknown_models). Zero runtime dependencies (stdlib + tree-sitter for
JS/TS). Path exclusions and per-path config via .tokentoll.yml.

Adoption so far: merged into assafelovic/gpt-researcher (27k stars) and a
handful of smaller AI apps. Would love feedback on SDK patterns I'm missing or
false positives you run into.

## Posting notes

- Best time: Sunday 00:00-02:00 UTC (Saturday evening US Pacific, lowest competition)
- Weekday alternative: Tuesday-Thursday 14:00-17:00 UTC
- Link post format (title + URL, no body text)
- Post the first comment immediately after submitting
- Respond to every comment within an hour
- Do NOT frame as "AI tool", frame as developer cost visibility
- Do NOT ask anyone to upvote via direct link (HN detects voting rings)
