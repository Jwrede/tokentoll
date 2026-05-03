# tokentoll -- Task Tracker

## Phase 1: Foundation (Days 1-2)

- [x] Project scaffolding (pyproject.toml, dirs, LICENSE, .gitignore)
- [x] GitHub repo created (Jwrede/tokentoll)
- [x] README skeleton
- [x] CLI entry point with argparse (scan, diff, update subcommands)
- [ ] Core models (LLMCall, CostEstimate, CallDiff, DiffReport)
- [ ] Python scanner (AST parsing, import detection, shared helpers)
- [ ] OpenAI detector (chat.completions.create, responses.create, embeddings.create)
- [ ] Pricing engine (load bundled JSON, model name normalization, cost calc)
- [ ] Bundle LiteLLM pricing data (model_prices.json)
- [ ] Table output formatter for scan command
- [ ] Wire up scan pipeline (scanner -> detectors -> pricing -> output)
- [ ] Tests: OpenAI detector
- [ ] Tests: pricing engine
- [ ] Initial commit + push

## Phase 2: Diff Engine (Days 3-4)

- [ ] Git operations module (changed files, file-at-ref)
- [ ] Diff engine (match old vs new calls by file + line proximity)
- [ ] Pipeline orchestrator for diff (scan both refs, price, diff)
- [ ] Table output for diff results (+/-/~ formatting)
- [ ] Wire up diff CLI command
- [ ] Tests: git operations
- [ ] Tests: diff engine
- [ ] Tests: integration (temp git repo, end-to-end)

## Phase 3: More Detectors (Days 5-6)

- [ ] Anthropic detector (messages.create, messages.stream)
- [ ] Google GenAI detector (models.generate_content)
- [ ] LiteLLM detector (completion, acompletion, embedding)
- [ ] LangChain detector (ChatOpenAI, ChatAnthropic, init_chat_model)
- [ ] Detector registry (auto-discover all detectors)
- [ ] Tests: Anthropic detector
- [ ] Tests: Google detector
- [ ] Tests: LiteLLM detector
- [ ] Tests: LangChain detector

## Phase 4: GitHub Action (Days 7-8)

- [ ] Markdown output formatter (PR comment with table, emoji status, assumptions)
- [ ] JSON output formatter
- [ ] action.yml (composite GitHub Action)
- [ ] Example workflow in README
- [ ] Dogfood: open test PR on tokentoll repo, verify comment
- [ ] GitHub topics: llm, openai, anthropic, cost-optimization, github-action, devtools, mlops

## Phase 5: Polish & Launch (Days 9-10)

- [ ] Token estimation improvements (optional tiktoken support)
- [ ] Pricing updater command (fetch latest from LiteLLM)
- [ ] Weekly pricing update cron (.github/workflows/update-pricing.yml)
- [ ] CI workflow (.github/workflows/ci.yml)
- [ ] Demo GIF for README (asciinema or vhs)
- [ ] PyPI publish (python -m build && twine upload)
- [ ] GitHub release v0.1.0
- [ ] Run marketing launch (see below)

## Marketing

### Pre-Launch (during build)

- [ ] X/Twitter: problem statement post (day 1)
- [ ] X/Twitter: working demo screenshot (day 4)
- [ ] X/Twitter: PR comment screenshot (day 7)

### Launch Day

- [ ] Write scripts/marketing/hn_post.md (Show HN post)
- [ ] Write scripts/marketing/reddit_mlops.md
- [ ] Write scripts/marketing/reddit_python.md
- [ ] Write scripts/marketing/reddit_devops.md
- [ ] Write scripts/marketing/devto_article.md (blog: 70% problem, 30% tool)
- [ ] Write scripts/marketing/linkedin_post.md (German AI community)
- [ ] Write scripts/marketing/tweets.md (launch thread)
- [ ] Submit to Hacker News (manual paste from hn_post.md)
- [ ] Post to Reddit (r/mlops, r/Python, r/devops)
- [ ] Publish to Dev.to (via API: curl)
- [ ] Post to LinkedIn

### Post-Launch

- [ ] Submit to awesome-llmops list (gh pr create)
- [ ] Submit to awesome-mlops list (gh pr create)
- [ ] Product Hunt listing (via API)
- [ ] GitHub Marketplace listing (auto from action.yml + release)
- [ ] Blog post #2: "How to estimate LLM API costs with static analysis"
