# GitHub Actions

Workflows:

| File | Role |
|------|------|
| `workflows/ci.yml` | Format, lint, types, offline tests, pip-audit, gitleaks |
| `workflows/ai-eval.yml` | Demo smoke + quality gate (path filter or label `run-ai-eval`) |
| `workflows/nightly-eval.yml` | Full 20-case demo (+ optional live_judge) |

Pushing or updating `.github/workflows/*` requires a personal access token (or credential) with the **`workflow`** scope. If `git push` rejects workflow changes, create a classic PAT with `repo` + `workflow`, then push with that credential once.
