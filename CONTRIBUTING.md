# Contributing to EcoCode

Thanks for considering a contribution to EcoCode.

## Development Setup (Python Core)

1. Create and activate a virtual environment.
2. Install package in editable mode with dev tools:
   - `python -m pip install -e .`
   - `python -m pip install pytest`
3. Run tests with `pytest`.

## Branch and PR Workflow

1. Create a branch: `feat/<short-name>` or `fix/<short-name>`.
2. Keep PRs focused and small.
3. Add or update tests for behavior changes.
4. Open a PR with context, approach, and before/after behavior.

## Commit Convention

Use conventional commits:
- `feat: add cpu profiler sampler`
- `fix: handle missing script in profile command`
- `docs: expand roadmap phase 2 milestones`

## Issue Triage Labels

Use these labels for consistency:
- `good first issue`
- `help wanted`
- `phase:core`
- `phase:workflow`
- `phase:cloud`
- `phase:ai`
