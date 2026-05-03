# tokentoll -- Task Tracker

## Day 1: Build Everything

### Core (morning)

- [x] Project scaffolding (pyproject.toml, dirs, LICENSE, .gitignore)
- [x] GitHub repo created (Jwrede/tokentoll)
- [x] README skeleton
- [x] CLI entry point with argparse (scan, diff, update subcommands)
- [x] Initial commit + push
- [ ] Core models (LLMCall, CostEstimate, CallDiff, DiffReport)
- [ ] Python scanner (AST parsing, import detection, shared helpers)
- [ ] OpenAI detector (chat.completions.create, responses.create, embeddings.create)
- [ ] Pricing engine (local cache ~/.tokentoll/, auto-refresh, bundled fallback, model name normalization, cost calc)
- [ ] Pricing cache logic (< 7d silent, 7-30d warn, > 30d error, unknown model warn)
- [ ] Bundle LiteLLM pricing data (model_prices.json) as fallback
- [ ] Table output formatter for scan command
- [ ] Wire up scan pipeline (scanner -> detectors -> pricing -> output)

### Diff engine (midday)

- [ ] Git operations module (changed files, file-at-ref)
- [ ] Diff engine (match old vs new calls by file + line proximity)
- [ ] Pipeline orchestrator for diff (scan both refs, price, diff)
- [ ] Table output for diff results (+/-/~ formatting)
- [ ] Wire up diff CLI command

### More detectors (afternoon)

- [ ] Anthropic detector (messages.create, messages.stream)
- [ ] Google GenAI detector (models.generate_content)
- [ ] LiteLLM detector (completion, acompletion, embedding)
- [ ] LangChain detector (ChatOpenAI, ChatAnthropic, init_chat_model)
- [ ] Detector registry (auto-discover all detectors)

### GitHub Action + polish (evening)

- [ ] Markdown output formatter (PR comment with table, emoji status, assumptions)
- [ ] JSON output formatter
- [ ] action.yml (composite GitHub Action)
- [ ] CI workflow (.github/workflows/ci.yml)
- [ ] Pricing updater command (fetch latest from LiteLLM)
- [ ] Tests: detectors, pricing, diff, integration
- [ ] PyPI publish (python -m build && twine upload)
- [ ] GitHub release v0.1.0
- [ ] GitHub topics: llm, openai, anthropic, cost-optimization, github-action, devtools, mlops

## Day 2: Test, Polish, Launch Prep

### Validation (before anything else)

- [ ] Run `tokentoll scan` on your litellm fork -- verify it finds real LLM calls
- [ ] Run `tokentoll scan` on your instructor fork -- verify multi-SDK detection
- [ ] Run `tokentoll scan` on your promptfoo fork -- verify no crashes on large codebase
- [ ] Clone langchain and run `tokentoll scan` -- stress test against hundreds of LLM calls
- [ ] Clone crewai or autogen and run `tokentoll scan` -- verify cross-SDK coverage
- [ ] Dogfood: open test PR on tokentoll repo, verify GitHub Action posts correct comment
- [ ] Fix any bugs found above

### Polish

- [ ] Demo GIF for README (asciinema or vhs)
- [ ] Final README polish (architecture diagram, badges)
- [ ] Write all marketing copy (see below)

## Day 3: Launch Day (all at once for max trending signal)

### Morning (~9am ET, Tue/Wed for peak traffic)

- [ ] Submit Show HN (manual paste from hn_post.md)
- [ ] Post X/Twitter launch thread
- [ ] Post to LinkedIn

### Staggered by 1-2 hours

- [ ] Post to r/mlops
- [ ] Post to r/Python
- [ ] Post to r/devops
- [ ] Publish Dev.to article (via API: curl)

## Post-Launch (week 1-2)

- [ ] Submit to awesome-llmops list (gh pr create)
- [ ] Submit to awesome-mlops list (gh pr create)
- [ ] Product Hunt listing (via API)
- [ ] GitHub Marketplace listing (auto from action.yml + release)
- [ ] Blog post: "How I built Infracost for LLM spend in a day"
- [ ] Weekly pricing update cron (.github/workflows/update-pricing.yml)
- [ ] Optional: tiktoken support for better token estimation

## Marketing Copy (all in scripts/marketing/, written day 2)

- [ ] hn_post.md -- "Show HN: tokentoll -- Catch LLM cost changes in code review"
- [ ] tweets.md -- launch thread (problem -> demo -> architecture -> link)
- [ ] reddit_mlops.md -- r/mlops post
- [ ] reddit_python.md -- r/Python post
- [ ] reddit_devops.md -- r/devops post
- [ ] devto_article.md -- "A model swap costs 15x more and nobody noticed"
- [ ] linkedin_post.md -- targeting German AI / ML community
- [ ] blog_speed_build.md -- "How I built Infracost for LLM spend in a day"
