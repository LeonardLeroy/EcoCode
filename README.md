# EcoCode

EcoCode is an open-source toolkit to measure, analyze, and optimize software energy consumption.

The project starts with a robust CLI core and expands toward workflow integrations, cloud auditing, and later local AI-assisted refactoring.

## Vision

- Build practical tooling for Green IT and sustainable software engineering.
- Make energy impact visible in local development and CI pipelines.
- Provide a contributor-friendly ecosystem with clear milestones.

## Current Status

Phase 1 has started with a first functional Python CLI prototype.

- Commands available:
	- `ecocode profile <script>`
	- `ecocode baseline create <script> -o <file>`
	- `ecocode baseline compare <script> --baseline <file>`
	- `ecocode profile-repo --root <path>`
	- `ecocode trend`
- Output modes: human-readable and JSON (`--json`)
- Optional run history persistence: `--save-run`
- Config support via `ecocode.toml`
- Scope: deterministic placeholder metrics, ready to be replaced by real runtime collectors

## Features

### Script profiling

- Profile one script and get CPU, memory, estimated Wh, and sustainability score.
- Supports JSON output for automation.

Examples:
- `ecocode profile path/to/script.py`
- `ecocode profile path/to/script.py --json`
- `ecocode profile path/to/script.py --save-run`

### Baseline creation and regression checks

- Create a baseline snapshot from a script run.
- Compare current run against baseline.
- Returns non-zero exit code on regression (`2`) for CI integration.

Examples:
- `ecocode baseline create path/to/script.py -o .ecocode/baseline.json`
- `ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json`
- `ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json --energy-threshold-pct 5`

### Repository-wide profiling

- Scan and profile supported source files in a repository.
- Supports extension filters and max files limits.
- Supports SARIF export for CI and code-scanning integrations.

Examples:
- `ecocode profile-repo --root .`
- `ecocode profile-repo --root . --ext .py --ext .js --max-files 100`
- `ecocode profile-repo --root . --json --save-run`
- `ecocode profile-repo --root . --sarif-output .ecocode/reports/ecocode.sarif`

### Trend analysis

- Read saved audit history and summarize progression over time.
- Supports command filter, limit, JSON output, and CSV export.

Examples:
- `ecocode trend`
- `ecocode trend --json`
- `ecocode trend --command profile-repo --limit 20 --json`
- `ecocode trend --csv-output .ecocode/reports/trend.csv`

### Audit history tracking

- Save audit runs to a local history directory for progress tracking.
- Configure behavior in `ecocode.toml`.
- Default history path: `.ecocode/history`.

### Project configuration (`ecocode.toml`)

- `history.enabled`: enable or disable local history writing.
- `history.auto_save`: save runs automatically without `--save-run`.
- `history.dir`: set custom history directory.
- `baseline.energy_threshold_pct`: default threshold for baseline compare.
- `profile_repo.max_files`: default max files for repository profiling.

### Reliability and Validation

- The current metric engine is deterministic placeholder logic for workflow validation.
- Test suite verifies CLI flows, JSON contracts, SARIF export, trend outputs, and aggregation consistency.
- Use this command before any PR: `.venv/bin/python -m pytest -q`
- Next reliability phase will introduce real runtime collectors and calibration.

## Repository Structure

```text
.
├── .github/ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── config.yml
│   └── feature_request.md
├── docs/
│   └── ROADMAP.md
├── implementations/
│   ├── cpp/
│   ├── csharp/
│   └── rust/
├── src/ecocode/
│   ├── __init__.py
│   ├── cli.py
│   ├── commands/
│   │   ├── baseline.py
│   │   ├── profile.py
│   │   ├── profile_repo.py
│   │   └── trend.py
│   └── core/
│       ├── config.py
│       ├── history.py
│       ├── profiler.py
│       ├── repository_profiler.py
│       ├── sarif.py
│       └── trend.py
├── tests/
│   ├── test_cli.py
│   ├── test_config_and_history.py
│   ├── test_profile_repo.py
│   └── test_trend.py
├── CONTRIBUTING.md
├── pyproject.toml
└── README.md
```

## Quick Start (Python Core)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

Run CLI help:

```bash
ecocode --help
```

Run the profile prototype:

```bash
ecocode profile path/to/script.py
ecocode profile path/to/script.py --json
ecocode profile path/to/script.py --save-run
ecocode profile-repo --root .
ecocode profile-repo --root . --ext .py --json
ecocode profile-repo --root . --save-run

ecocode baseline create path/to/script.py -o .ecocode/baseline.json --save-run
ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json

```

Optional project configuration (`ecocode.toml`):

```toml
[history]
enabled = true
auto_save = false
dir = ".ecocode/history"

[baseline]
energy_threshold_pct = 5.0

[profile_repo]
max_files = 50
```

Run tests:

```bash
.venv/bin/python -m pytest -q
```

## Multi-Platform and Multi-Language Strategy

- Primary delivery now: Python reference CLI (fast iteration, contributor-friendly)
- Next performance path: Rust collector engine
- Ecosystem expansions: C++ and C# integration tracks
- Platform support target:
	- Linux and Windows first
	- macOS immediately after core stabilization

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed phases and a suggested initial issue backlog.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
