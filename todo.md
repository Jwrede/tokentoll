# tokentoll -- Task Tracker

## Day 1: Build Everything

### Core (morning)

- [x] Project scaffolding (pyproject.toml, dirs, LICENSE, .gitignore)
- [x] GitHub repo created (Jwrede/tokentoll)
- [x] README skeleton
- [x] CLI entry point with argparse (scan, diff, update subcommands)
- [x] Initial commit + push
- [x] Core models (LLMCall, CostEstimate, CallDiff, DiffReport)
- [x] Python scanner (AST parsing, import detection, shared helpers)
- [x] OpenAI detector (chat.completions.create, responses.create, embeddings.create)
- [x] Pricing engine (local cache ~/.tokentoll/, auto-refresh, bundled fallback, model name normalization, cost calc)
- [x] Pricing cache logic (< 7d silent, 7-30d warn, > 30d error, unknown model warn)
- [x] Bundle LiteLLM pricing data (model_prices.json) as fallback
- [x] Table output formatter for scan command
- [x] Wire up scan pipeline (scanner -> detectors -> pricing -> output)

### Diff engine (midday)

- [x] Git operations module (changed files, file-at-ref)
- [x] Diff engine (match old vs new calls by file + line proximity)
- [x] Pipeline orchestrator for diff (scan both refs, price, diff)
- [x] Table output for diff results (+/-/~ formatting)
- [x] Wire up diff CLI command

### More detectors (afternoon)

- [x] Anthropic detector (messages.create, messages.stream)
- [x] Google GenAI detector (models.generate_content)
- [x] LiteLLM detector (completion, acompletion, embedding)
- [x] LangChain detector (ChatOpenAI, ChatAnthropic, init_chat_model)
- [x] Detector registry (auto-discover all detectors)

### GitHub Action + polish (evening)

- [x] Markdown output formatter (PR comment with table, emoji status, assumptions)
- [x] JSON output formatter
- [x] action.yml (composite GitHub Action)
- [x] CI workflow (.github/workflows/ci.yml)
- [x] Pricing updater command (fetch latest from LiteLLM)
- [x] Tests: detectors, pricing, diff, integration (38 tests, all passing)
- [x] PyPI publish v0.1.0 (twine upload dist/*)
- [x] GitHub release v0.1.0
- [x] GitHub topics: llm, openai, anthropic, cost-optimization, github-action, devtools, mlops

## Day 2: Test, Polish, Launch Prep

### Validation

- [x] Run `tokentoll scan` on litellm -- 1,387 calls detected
- [x] Run `tokentoll scan` on instructor -- 10 calls detected
- [x] Run `tokentoll scan` on promptfoo -- 5 calls detected
- [x] Run `tokentoll scan` on langchain -- 429 calls detected
- [x] Run `tokentoll scan` on crewai -- 3 calls detected
- [x] Dogfood: opened test PR #1, GitHub Action posted correct cost diff comment
- [x] Fix bugs found (Bedrock region prefix resolution)

### Polish

- [x] Final README polish (architecture diagram, badges)
- [x] Write all marketing copy (8 files in scripts/marketing/)
- [x] Demo recording (asciinema: https://asciinema.org/a/H1bhVFIiPqUE0Shh)

## Day 2.5: Deep Variable Resolution

- [x] Multi-pass constant propagation engine (5 propagation passes to fixed point)
- [x] Variable-to-variable resolution (x = y where y is known)
- [x] os.getenv() / os.environ.get() fallback extraction
- [x] Function default argument tracking
- [x] Class attribute defaults and self.x = y in __init__
- [x] Constructor argument propagation (obj = Cls(val) -> obj.attr)
- [x] Dict literal/subscript contents (d["key"] = val)
- [x] **kwargs unpacking resolution (create(**d) resolves d.model)
- [x] Instance attribute inheritance from class-level defaults
- [x] All detectors updated for kwargs resolution
- [x] 9 new tests (47 total, all passing)
- [x] PyPI publish v0.2.0
- [x] GitHub release v0.2.0

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
- [x] Weekly pricing update cron (.github/workflows/update-pricing.yml)
- [ ] Optional: tiktoken support for better token estimation

## Marketing Copy (all in scripts/marketing/)

- [x] hn_post.md -- "Show HN: tokentoll -- Catch LLM cost changes in code review"
- [x] tweets.md -- launch thread (problem -> demo -> architecture -> link)
- [x] reddit_mlops.md -- r/mlops post
- [x] reddit_python.md -- r/Python post
- [x] reddit_devops.md -- r/devops post
- [x] devto_article.md -- "A model swap costs 15x more and nobody noticed"
- [x] linkedin_post.md -- targeting German AI / ML community
- [x] blog_speed_build.md -- "How I built Infracost for LLM spend in a day"
