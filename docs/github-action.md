# GitHub Action reference

The tokentoll GitHub Action runs `tokentoll diff` on every pull request, posts a verdict comment, and (optionally) fails the workflow when the policy is violated.

## Minimal workflow

```yaml
name: tokentoll
on:
  pull_request:
    paths:
      - "**.py"
      - "**.ts"
      - "**.tsx"
      - "**.js"
      - "**.jsx"

permissions:
  contents: read
  pull-requests: write

jobs:
  cost-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Jwrede/tokentoll@v0.7.0
        with:
          fail-on-policy-violation: true
```

`fetch-depth: 0` is required so tokentoll can read both the base ref and the head ref.

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `github-token` | `${{ github.token }}` | Token used to post the PR comment. |
| `calls-per-month` | `1000` | Assumed monthly call volume per call site, used for dollar estimates. |
| `base-ref` | PR base SHA | Override the base of the diff. |
| `head-ref` | PR head SHA | Override the head of the diff. |
| `python-version` | `3.11` | Python version to install tokentoll on. |
| `fail-on-policy-violation` | `false` | If `true`, the action fails the workflow when the verdict is FAIL. The PR comment is posted first; the workflow fails after. |

## Outputs

| Output | Description |
|--------|-------------|
| `monthly-delta` | Net monthly cost delta in USD (positive = more expensive). |
| `verdict` | Policy verdict: `pass`, `warn`, or `fail`. |

These are exposed for downstream steps:

```yaml
      - uses: Jwrede/tokentoll@v0.7.0
        id: tokentoll
      - if: steps.tokentoll.outputs.verdict == 'fail'
        run: echo "PR exceeds cost policy"
```

## Permissions

The action needs `pull-requests: write` only to post the verdict comment. Without it, the action still runs and produces output, but cannot comment.

If you do not want comments at all, set `permissions: contents: read` only and the comment step will fail silently while the workflow still passes or fails based on the verdict.

For fork PRs, GitHub provides a read-only `GITHUB_TOKEN`, so the comment step will fail. The verdict is still computed and surfaced in the workflow logs. For full fork PR support, use the `pull_request_target` event with extreme care, because it runs against the base branch's workflow file and has access to secrets. Most users should not.

## SHA pinning

Pinning to a tagged release (`@v0.7.0`) is convenient but mutable: a re-tagged release would silently change behavior. For higher trust, pin to the commit SHA of the release:

```yaml
- uses: Jwrede/tokentoll@d2dc8ca7... # v0.7.0
```

You can find the SHA on the [releases page](https://github.com/Jwrede/tokentoll/releases).

## Common patterns

### Comment-only (report, never block)

```yaml
- uses: Jwrede/tokentoll@v0.7.0
  # fail-on-policy-violation defaults to false
```

The verdict is posted; the workflow always passes.

### Block on policy violation

```yaml
- uses: Jwrede/tokentoll@v0.7.0
  with:
    fail-on-policy-violation: true
```

The verdict is posted, then the workflow fails if it is FAIL. Use this with branch protection rules to make the gate actually enforce.

### Different policies per branch

Set `fail-on-policy-violation: ${{ github.base_ref == 'main' }}` so the workflow only fails when merging into `main`, while keeping all other branches in comment-only mode.

## How the workflow flow looks

1. `actions/setup-python` installs Python 3.11 (or your override).
2. `pip install tokentoll==0.7.0` (pinned by the action).
3. `tokentoll diff --format=json` runs once to capture machine output and extract the verdict + delta.
4. `tokentoll diff --format=github-comment` runs once to render the markdown comment.
5. If the PR adds tokentoll itself and detects no cost changes, a short install-confirmation comment is posted instead. There is no whole-repo baseline scan.
6. `marocchino/sticky-pull-request-comment@v2` updates the PR's sticky tokentoll comment in place.
7. If `fail-on-policy-violation: true` and the verdict is FAIL, the workflow exits 1 with an `::error::` annotation.

## Troubleshooting

- **"No Python files changed."** The diff between base and head contains no Python changes. Expected on doc-only PRs.
- **Comment doesn't appear on fork PR.** GitHub provides a read-only token for fork PRs. The verdict is still computed; check the workflow logs.
- **Verdict says PASS but you expected FAIL.** Confirm `.tokentoll.yml` is at the repo root and lists at least one budget or rule. An empty policy always produces PASS.
- **Unknown model showing as `(default)`.** tokentoll could not resolve the model name statically and fell back to the per-SDK default. Set the model with a string literal, configure `default_models`, or enable `block_unknown_models` to surface this.
