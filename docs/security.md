# Security

tokentoll is built to be safe to install on any repository. This document covers the trust model, what tokentoll reads or writes, and the recommended hardening for CI use.

## Trust model in one paragraph

tokentoll is a static analyzer plus a markdown renderer. It reads source files and git history, runs a Python AST pass to find LLM API call sites, looks up pricing in a bundled JSON file, and emits a report. It never executes the analyzed code, never makes outbound network requests at scan time, and never requires a secret to operate. The GitHub Action's only privileged operation is posting a sticky PR comment via the standard `GITHUB_TOKEN`.

## What tokentoll does NOT do

- It does not require an API key from any LLM provider. It does not call OpenAI, Anthropic, Google, or any other provider at scan time.
- It does not send telemetry. There is no opt-out flag because there is nothing to opt out of.
- It does not execute the analyzed code. Detection is pure AST traversal.
- It does not modify your source tree. Edits are out of scope.
- It does not store anything outside of `~/.tokentoll/` (the pricing cache) on developer machines, and `/tmp/tokentoll-comment.md` inside the Action runner.

## Network access

The CLI is fully offline at scan time. The only command that touches the network is `tokentoll update`, which fetches the latest LiteLLM pricing snapshot from the LiteLLM GitHub repo. The Action does not run `tokentoll update`; it uses the pricing data shipped inside the installed package version.

## Permissions for the GitHub Action

The minimum permission set:

```yaml
permissions:
  contents: read
  pull-requests: write
```

- `contents: read` is required to check out the code via `actions/checkout`.
- `pull-requests: write` is required to post the verdict comment.

If you do not want PR comments, drop `pull-requests: write`. The action will still run, compute the verdict, and (if configured) fail the workflow; only the comment-posting step will error.

The action does not use any other GitHub scope (no issues, no checks API, no actions, no contents:write).

## Fork PR risk

GitHub provides a read-only `GITHUB_TOKEN` for pull requests opened from forks. With the recommended permission block above, tokentoll degrades cleanly: the verdict is still computed and surfaced in the workflow logs, but the comment-posting step fails because the token cannot write to PRs from forks.

`pull_request_target` does work for fork PRs and has write access to the base repo's secrets and PR comments, but it runs the workflow file from the base branch and gives the contents of the fork PR access to those secrets. Most projects should not use `pull_request_target` with tokentoll. If you need to comment on fork PRs, accept the lost comment and read the verdict from the workflow log or the `verdict` output, or use a workflow split (untrusted analyze + trusted comment-post) as described in [GitHub's blog post on fork PR security](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/).

## SHA pinning

Tags (`@v0.7.0`) can be moved. For a stronger guarantee that an upgrade requires an explicit decision, pin to a commit SHA:

```yaml
- uses: Jwrede/tokentoll@d2dc8ca7...   # v0.7.0
```

SHAs are listed alongside each tag on the [releases page](https://github.com/Jwrede/tokentoll/releases).

If you want to be defended against the PyPI package itself being compromised, additionally pin the action's `pip install` line by forking the repo, locking the version, and using your fork. This is rarely worth it for tooling at this scale, but it is an option.

## Pricing data source

Pricing data is sourced from [BerriAI/litellm](https://github.com/BerriAI/litellm)'s `model_prices_and_context_window.json`. Each tokentoll release bundles a known-good snapshot. Running `tokentoll update` overwrites the local cache with the latest LiteLLM snapshot; the Action does not do this, so reported costs are deterministic per tokentoll version.

If you do not trust LiteLLM's pricing data, you can ship your own `~/.tokentoll/model_prices.json` (same schema) and tokentoll will pick it up instead.

## Reporting security issues

Open a private security advisory at https://github.com/Jwrede/tokentoll/security/advisories. Do not file a public issue for vulnerabilities.

For non-security bugs, regular GitHub issues are fine.
