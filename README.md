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
	- `ecocode benchmark --fixtures-dir <path>`
	- `ecocode trend`
- Output modes: human-readable and JSON (`--json`)
- JSON outputs are validated against internal schemas before emission.
- Optional run history persistence: `--save-run`
- Config support via `ecocode.toml`
- Scope: deterministic placeholder metrics, ready to be replaced by real runtime collectors
- Runtime collection preview: `--collector runtime` (Linux/macOS/Windows)
- Repeated-run mode for stability analysis: `--runs <n>`
- Linux runtime collector samples process groups to include subprocess activity.
- Windows runtime collector preview samples process working-set memory for profiled scripts.
- Calibration factors configurable via `ecocode.toml`.
- Stability gate options: `--max-energy-cv-pct` and `--fail-on-unstable`.

## Features

### Script profiling

- Profile one script and get CPU, memory, estimated Wh, and sustainability score.
- Supports JSON output for automation.
- Supports collector selection: `--collector placeholder|runtime`.
- Supports repeated-run statistics with `--runs` (mean/median/stddev).

Examples:
- `ecocode profile path/to/script.py`
- `ecocode profile path/to/script.py --collector runtime`
- `ecocode profile path/to/script.py --collector runtime --runs 5 --json`
- `ecocode profile path/to/script.py --collector runtime --runs 5 --max-energy-cv-pct 20 --fail-on-unstable --json`
- `ecocode profile path/to/script.py --json`
- `ecocode profile path/to/script.py --save-run`

### Baseline creation and regression checks

- Create a baseline snapshot from a script run.
- Compare current run against baseline.
- Returns non-zero exit code on regression (`2`) for CI integration.

Examples:
- `ecocode baseline create path/to/script.py -o .ecocode/baseline.json`
- `ecocode baseline create path/to/script.py -o .ecocode/baseline.json --collector runtime`
- `ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json`
- `ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json --energy-threshold-pct 5`
- `ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json --collector runtime --runs 5 --json`

### Repository-wide profiling

- Scan and profile supported source files in a repository.
- Supports extension filters and max files limits.
- Supports include/exclude path globs for tighter scan scopes.
- Supports SARIF export for CI and code-scanning integrations.

Examples:
- `ecocode profile-repo --root .`
- `ecocode profile-repo --root . --collector runtime`
- `ecocode profile-repo --root . --collector runtime --runs 3 --json`
- `ecocode profile-repo --root . --ext .py --ext .js --max-files 100`
- `ecocode profile-repo --root . --ext .py --include-glob "src/**/*.py" --exclude-glob "tests/*.py" --json`
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

### Benchmark reproducibility

- Run deterministic fixture scripts repeatedly and evaluate stability.
- Reports median and coefficient of variation (CV) per fixture.
- Returns exit code `3` with `--fail-on-unstable` when any fixture exceeds CV threshold.

Examples:
- `ecocode benchmark`
- `ecocode benchmark --fixtures-dir benchmarks/fixtures --runs 7 --json`
- `ecocode benchmark --collector runtime --runs 5 --max-energy-cv-pct 20 --fail-on-unstable`

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
- `calibration.cpu_wh_per_cpu_second`: calibration factor for CPU energy estimation.
- `calibration.memory_wh_per_mb`: calibration factor for memory energy estimation.
- `stability.max_energy_cv_pct`: default max coefficient of variation (%%) over repeated runs.

### Reliability and Validation

- The current metric engine is deterministic placeholder logic for workflow validation.
- Runtime collector preview executes scripts with platform backends (Linux process-group sampling, macOS children usage, Windows working-set sampling).
- Repeated runs expose mean/median/stddev and CV to gate unstable measurements.
- Test suite verifies CLI flows, JSON contracts, SARIF export, trend outputs, and aggregation consistency.
- Central schema validation enforces stable JSON payload structures across commands.
- Use this command before any PR: `.venv/bin/python -m pytest -q`
- Next reliability phase will introduce real runtime collectors and calibration.

## Command Outputs And Interpretation

This section shows what each implemented command returns and how to interpret the values.

### 1) `ecocode profile`

Command:

```bash
ecocode profile path/to/script.py
```

Example text output:

```text
EcoCode profile report
Script:               /workspace/path/to/script.py
CPU time (s):         1.84
Memory peak (MB):     76.2
Estimated energy Wh:  0.357
Sustainability score: 90/100
```

Interpretation:
- `CPU time (s)`: effective CPU work consumed by the run. Lower is usually better.
- `Memory peak (MB)`: peak memory footprint observed. Spikes here often indicate heavy allocations.
- `Estimated energy Wh`: synthetic estimate from CPU and memory factors. Compare this across commits.
- `Sustainability score`: convenience score (`0-100`), where higher means lighter resource usage.

JSON variant:

```bash
ecocode profile path/to/script.py --runs 3 --json
```

Example JSON excerpt:

```json
{
	"script": "/workspace/path/to/script.py",
	"collector": "runtime",
	"runs": 3,
	"cpu_seconds": 1.92,
	"memory_mb": 80.3,
	"estimated_energy_wh": 0.3755,
	"sustainability_score": 89,
	"summary": {
		"estimated_energy_wh_mean": 0.3721,
		"estimated_energy_wh_median": 0.3718,
		"estimated_energy_wh_stddev": 0.0046,
		"estimated_energy_wh_cv_pct": 1.236
	}
}
```

Interpretation tips:
- Use `estimated_energy_wh_median` as the most stable baseline value.
- Use `estimated_energy_wh_cv_pct` to detect noisy runs. High CV means low measurement stability.

### 2) `ecocode baseline create`

Command:

```bash
ecocode baseline create path/to/script.py -o .ecocode/baseline.json --runs 5
```

Example CLI output:

```text
Baseline created: /workspace/.ecocode/baseline.json
```

Example generated file (`.ecocode/baseline.json`):

```json
{
	"version": 2,
	"collector": "placeholder",
	"runs": 5,
	"baseline": {
		"script": "/workspace/path/to/script.py",
		"cpu_seconds": 1.8,
		"memory_mb": 72.4,
		"estimated_energy_wh": 0.3442,
		"sustainability_score": 90
	},
	"statistics": {
		"estimated_energy_wh_mean": 0.3451,
		"estimated_energy_wh_median": 0.3442,
		"estimated_energy_wh_stddev": 0.0031,
		"cpu_seconds_median": 1.8,
		"memory_mb_median": 72.4
	}
}
```

Interpretation:
- This file is your reference snapshot. Keep it versioned for reproducible comparisons.
- The median values in `statistics` are usually the best anchors for regression checks.

### 3) `ecocode baseline compare`

Command:

```bash
ecocode baseline compare path/to/script.py --baseline .ecocode/baseline.json --runs 5 --json
```

Example JSON excerpt:

```json
{
	"threshold_pct": 5.0,
	"baseline_energy_wh": 0.3442,
	"current_energy_wh": 0.3591,
	"increase_pct": 4.3289,
	"regression": false,
	"status": "passed",
	"stability": {
		"max_energy_cv_pct": 35.0,
		"unstable": false
	}
}
```

Interpretation:
- `increase_pct > threshold_pct` means energy regression.
- Exit code `2` means regression detected.
- With `--fail-on-unstable`, exit code `3` means result quality is too noisy to trust.

### 4) `ecocode profile-repo`

Command:

```bash
ecocode profile-repo --root . --ext .py --runs 3 --json
```

Example JSON excerpt:

```json
{
	"root": "/workspace/repo",
	"total_files": 12,
	"total_cpu_seconds": 25.48,
	"total_memory_mb": 932.4,
	"total_energy_wh": 4.5692,
	"average_sustainability_score": 86.25,
	"summary": {
		"total_energy_wh_mean": 4.6112,
		"total_energy_wh_median": 4.5692,
		"total_energy_wh_stddev": 0.0713,
		"total_energy_wh_cv_pct": 1.546
	}
}
```

Interpretation:
- `total_energy_wh` is the aggregate footprint of scanned files for one run.
- `average_sustainability_score` is useful as a high-level health indicator across modules.
- For CI gates, prefer `summary.total_energy_wh_median` over single-run totals.

### 5) `ecocode benchmark`

Command:

```bash
ecocode benchmark --fixtures-dir benchmarks/fixtures --runs 7 --json
```

Example JSON excerpt:

```json
{
	"fixtures_dir": "/workspace/benchmarks/fixtures",
	"runs": 7,
	"max_energy_cv_pct": 20.0,
	"total_fixtures": 3,
	"unstable_fixtures": 1,
	"status": "unstable",
	"summary": {
		"energy_wh_mean": 0.1482,
		"energy_wh_median": 0.1421,
		"energy_wh_stddev": 0.0142,
		"energy_wh_cv_pct": 9.582
	}
}
```

Interpretation:
- This command measures reproducibility of benchmark fixtures.
- `unstable_fixtures` tells you how many fixtures exceeded CV threshold.
- With `--fail-on-unstable`, exit code `3` signals unstable benchmark quality.

### 6) `ecocode trend`

Command:

```bash
ecocode trend --command profile-repo --limit 20 --json
```

Example JSON excerpt:

```json
{
	"summary": {
		"count": 20,
		"first_energy_wh": 5.12,
		"last_energy_wh": 4.58,
		"min_energy_wh": 4.51,
		"max_energy_wh": 5.2,
		"delta_wh": -0.54,
		"delta_pct": -10.55
	}
}
```

Interpretation:
- `delta_wh` and `delta_pct` show progression between oldest and newest points.
- Negative delta indicates improvement (less estimated energy), positive means drift/regression.
- Use `--csv-output` when you want plotting in notebooks or dashboards.

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
├── benchmarks/
│   └── fixtures/
│       ├── cpu_loop_small.py
│       ├── list_transform.py
│       └── string_workload.py
├── src/ecocode/
│   ├── __init__.py
│   ├── cli.py
│   ├── commands/
│   │   ├── baseline.py
│   │   ├── benchmark.py
│   │   ├── profile.py
│   │   ├── profile_repo.py
│   │   └── trend.py
│   └── core/
│       ├── benchmark.py
│       ├── config.py
│       ├── history.py
│       ├── profiler.py
│       ├── repository_profiler.py
│       ├── sarif.py
│       ├── schemas.py
│       └── trend.py
├── tests/
│   ├── test_cli.py
│   ├── test_config_and_history.py
│   ├── test_profile_repo.py
│   ├── test_schemas.py
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

[calibration]
cpu_wh_per_cpu_second = 0.07
memory_wh_per_mb = 0.003

[stability]
max_energy_cv_pct = 35.0
```

Run tests:

```bash
.venv/bin/python -m pytest -q
```

## Multi-Platform and Multi-Language Strategy

- Primary delivery now: Python reference CLI
- Next performance path: Rust collector engine
- Ecosystem expansions: C++ and C# integration tracks
- Platform support target:
	- Linux and Windows first
	- macOS immediately after core stabilization

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed phases and a suggested initial issue backlog.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
