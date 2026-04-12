# Contributing to EcoCode

Thanks for considering a contribution to EcoCode.

## Development Setup (Python Core)

1. Create and activate a virtual environment.
2. Install package in editable mode with dev tools:
   - `python -m pip install -e .`
   - `python -m pip install pytest`
3. Run tests with `.venv/bin/python -m pytest -q`.

## Local Quality Gate (required before PR)

Before opening a PR, contributors must validate that the project is healthy locally:

1. Ensure the package installs in editable mode:
   - `.venv/bin/python -m pip install -e .`
2. Ensure tests pass:
   - `.venv/bin/python -m pytest -q`
3. Ensure Python sources compile:
   - `.venv/bin/python -m compileall src`
4. Re-run the CLI quickly to catch obvious regressions:
   - `.venv/bin/ecocode --help`
   - `.venv/bin/ecocode profile demo.py --json`
   - `.venv/bin/ecocode profile demo.py --collector runtime --json`
   - `.venv/bin/ecocode profile demo.py --collector runtime --runs 3 --json`
   - For subprocess-heavy changes, add a small runtime smoke check that spawns a child process.

PRs should be opened only after these checks pass.

## Branch and PR Workflow

1. Create a branch: `feat/<short-name>` or `fix/<short-name>`.
2. Keep PRs focused and small.
3. Add or update tests for behavior changes.
4. Run the Local Quality Gate checks.
5. Open a PR with context, approach, and before/after behavior.

## Commit Convention

Use conventional commits:
- `feat: add cpu profiler sampler`
- `fix: handle missing script in profile command`
- `test: add coverage for baseline regression`
- `docs: expand roadmap phase 2 milestones`

## Issue Triage Labels

Use these labels for consistency:
- `good first issue`
- `help wanted`
- `phase:core`
- `phase:workflow`
- `phase:cloud`
- `phase:ai`
