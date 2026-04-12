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
	- `ecocode optimize suggest <script>`
	- `ecocode optimize patch <script>`
	- `ecocode optimize evaluate --baseline <file> --candidate <file>`
	- `ecocode trend`
- Output modes: human-readable and JSON (`--json`)
- JSON outputs are validated against internal schemas before emission.
- JSON outputs include `schemaVersion` for compatibility-safe evolution.
- Optional run history persistence: `--save-run`
- Config support via `ecocode.toml`
- Scope: deterministic placeholder metrics, ready to be replaced by real runtime collectors
- Multi-language audit scope includes Python, C, C++, C#, Rust, JavaScript/TypeScript, HTML/CSS, and Assembly in repository scans.
- Repository profiling is extension-based, so it can audit mixed-language repos even when runtime execution support is narrower than static scanning.
- Runtime collection preview: `--collector runtime` (Linux/Windows; macOS deferred for now)
- Runtime collection sampling interval: `--sampling-interval <seconds>`
- Repeated-run mode for stability analysis: `--runs <n>`
- Linux runtime collector samples process groups to include subprocess activity.
- Linux runtime collector also samples cgroup memory usage (when available) for container-aware measurements.
- Windows runtime collector preview samples process working-set memory for profiled scripts.
- Calibration factors configurable via `ecocode.toml`.
- Stability gate options: `--max-energy-cv-pct` and `--fail-on-unstable`.

## Language Support Matrix

The repository audit is extension-based, so it can already scan mixed-language repositories. Runtime execution is narrower today, and the optimizer starts with deterministic suggestions before a future local LLM.

| Language | Repo audit | Runtime collector | Optimizer suggest | Notes |
| --- | --- | --- | --- | --- |
| Python | Yes | Yes | Yes | Strongest end-to-end support today. |
| C | Yes | Partial | Yes | Static audit + optimizer rules; runtime depends on executable form. |
| C++ | Yes | Partial | Yes | Static audit + optimizer rules; runtime depends on executable form. |
| C# | Yes | Partial | Yes | Static audit + optimizer rules; runtime depends on executable form. |
| Rust | Yes | Partial | Yes | Static audit + optimizer rules; runtime depends on executable form. |
| JavaScript / TypeScript | Yes | Partial | Yes | Good for repo audits; runtime execution is not universal yet. |
| HTML / CSS | Yes | No | Yes | Static audit only; optimizer can still flag patterns. |
| Assembly | Yes | No | Yes | Static audit only; useful for repository scans and rule-based advice. |
| Java | Yes | Partial | Planned | Repo scans are covered; runtime/optimizer maturity can improve later. |
| Go | Yes | Partial | Planned | Repo scans are covered; runtime maturity depends on executable packaging. |
| Ruby | Yes | Partial | Planned | Repo scans are covered; runtime maturity depends on executable packaging. |
| Shell | Yes | Partial | Planned | Useful for repo profiling and scripts; runtime may vary by environment. |

Legend:
- `Yes`: supported in the current implementation.
- `Partial`: supported in some cases, but not as a universal/runtime-native guarantee yet.
- `No`: not a runtime target today, but still may be scanned as text if extension rules match.

## Features

### Script profiling

- Profile one script and get CPU, memory, estimated Wh, and sustainability score.
- Supports JSON output for automation.
- Supports collector selection: `--collector placeholder|runtime`.
- Supports repeated-run statistics with `--runs` (mean/median/stddev).

Examples:
- `ecocode profile path/to/script.py`
- `ecocode profile path/to/script.py --collector runtime`
- `ecocode profile path/to/script.py --collector runtime --sampling-interval 0.01`
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
- Default discovery now covers common extensions for Python, C/C++, C#, Rust, JavaScript/TypeScript, HTML/CSS, and Assembly.

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
- Supports noise profiles: `idle`, `warm`, `cpu-bound`.
- Reports per-fixture CV and suite-level CV with acceptance thresholds.
- Returns exit code `3` with `--fail-on-unstable` when any fixture exceeds per-fixture CV threshold.
- Returns exit code `4` with `--fail-on-acceptance` when acceptance thresholds are not met.

Examples:
- `ecocode benchmark`
- `ecocode benchmark --fixtures-dir benchmarks/fixtures --noise-profile cpu-bound --json`
- `ecocode benchmark --collector runtime --runs 5 --max-energy-cv-pct 20 --fail-on-unstable`
- `ecocode benchmark --max-suite-cv-pct 8 --max-unstable-fixtures 0 --fail-on-acceptance --json`

### Optimizer suggestions (MVP)

- Rule-based optimization suggestions for source files.
- Works as deterministic fallback before local LLM integration.
- Supports JSON output for CI/report pipelines.
- Supports candidate evaluation against baseline gates (`optimize evaluate`).

Workflow:
1. Create a baseline with `ecocode baseline create`.
2. Inspect hotspots with `ecocode optimize suggest`.
3. Generate a candidate with `ecocode optimize patch` (auto or with `--rule-id`).
4. Verify improvement with `ecocode optimize evaluate`.
5. Keep only candidates that improve energy/performance without failing regression gates.

Examples:
- `ecocode optimize suggest path/to/script.py`
- `ecocode optimize suggest path/to/script.py --json`
- `ecocode optimize suggest path/to/source.cpp --max-suggestions 5 --json`
- `ecocode optimize patch path/to/script.py --json`
- `ecocode optimize patch path/to/script.py --rule-id PY001 --output path/to/candidate.py --json`
- `ecocode optimize patch path/to/script.py --use-llm --json`
- `ecocode optimize evaluate --baseline .ecocode/baseline.json --candidate path/to/candidate.py --json`

Notes:
- `optimize suggest` is deterministic today, so the same file yields the same rule hits.
- `optimize patch` currently applies safe deterministic Python strategies (MVP scope).
- `optimize patch --use-llm` can generate a local-model candidate patch when `[optimize.llm]` is enabled.
- `optimize evaluate` compares candidate energy against the baseline median and applies stability gates.
- The deterministic optimizer is the bridge to local LLMs later, because the validation path already exists.

### Local LLM setup (Ollama)

To enable local-model suggestions in `optimize suggest`:

1. Install Ollama.
2. Pull a coding model (recommended first choice: `qwen2.5-coder:7b`).
3. Configure `ecocode.toml`:

```toml
[optimize.llm]
enabled = true
provider = "ollama"
model = "qwen2.5-coder:7b"
max_suggestions = 3
timeout_seconds = 20.0
```

Model guidance:
- There is no universal single best model for every machine and codebase.
- Prefer coding-focused models (`qwen2.5-coder`, `deepseek-coder`, `codellama`) over general MoE chat models.

### Output modes

- By default, commands print human-readable output.
- JSON output is optional and mainly intended for CI/automation.
- Use `--json` only when you need machine-readable data.

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
- `optimize.enabled`: enable or disable `optimize patch`.
- `optimize.allowed_patch_rule_ids`: restrict which patch rules the team accepts.
- `optimize.default_patch_rule_id`: default rule used when `optimize patch` is run without `--rule-id`.
- `optimize.max_patch_changes`: maximum number of edits a patch can apply before being rejected.
- `optimize.llm.enabled`: enable local LLM suggestions as an optional layer on top of deterministic suggestions.
- `optimize.llm.provider`: local provider backend (`none`, `ollama`).
- `optimize.llm.model`: local model name used by the provider (recommended: `qwen2.5-coder:7b` or better).
- `optimize.llm.max_suggestions`: cap for LLM-proposed suggestions merged into output.
- `optimize.llm.timeout_seconds`: timeout for local provider requests.

### Reliability and Validation

- The current metric engine is deterministic placeholder logic for workflow validation.
- Runtime collector preview executes scripts with platform backends (Linux process-group + cgroup-aware memory sampling, macOS children usage, Windows working-set sampling).
- Repeated runs expose mean/median/stddev and CV to gate unstable measurements.
- Test suite verifies CLI flows, JSON contracts, SARIF export, trend outputs, and aggregation consistency.
- Central schema validation enforces stable JSON payload structures across commands.
- A GitHub Actions workflow prototype runs `profile-repo` on CI and publishes SARIF/artifacts.
- Use this command before any PR: `.venv/bin/python -m pytest -q`
- Next reliability phase will introduce real runtime collectors and calibration.

### CI automation prototype

- Workflow file: `.github/workflows/ecocode-profile-repo.yml`
- Trigger: pull requests, pushes to `main`, or manual dispatch.
- Behavior:
	- installs EcoCode,
	- runs `ecocode profile-repo --json --sarif-output ...`,
	- uploads JSON + SARIF artifacts,
	- attempts SARIF publication to GitHub code scanning.

### Schema compatibility policy

- All machine-readable command outputs include `schemaVersion`.
- Current schema version is `1`.
- Compatibility rule: new fields can be added in a backward-compatible way, while removals or semantic changes require a schema version bump and migration notes.

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
ecocode benchmark --fixtures-dir benchmarks/fixtures --noise-profile warm --json
```

Example JSON excerpt:

```json
{
	"schemaVersion": 1,
	"fixtures_dir": "/workspace/benchmarks/fixtures",
	"noise_profile": "warm",
	"runs": 7,
	"max_energy_cv_pct": 20.0,
	"max_suite_cv_pct": 10.0,
	"max_unstable_fixtures": 0,
	"total_fixtures": 3,
	"unstable_fixtures": 1,
	"status": "failed",
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
- `noise_profile` applies tuned defaults for run count and acceptance thresholds.
- `unstable_fixtures` counts fixtures above per-fixture CV threshold.
- `status` reports acceptance outcome from suite-level gates.
- `--fail-on-unstable` returns exit `3` when any fixture exceeds per-fixture CV limits.
- `--fail-on-acceptance` returns exit `4` when full suite acceptance fails.

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

### 7) `ecocode optimize suggest`

Command:

```bash
ecocode optimize suggest path/to/script.py --json
```

Example JSON excerpt:

```json
{
	"schemaVersion": 1,
	"command": "optimize suggest",
	"script": "/workspace/path/to/script.py",
	"suggestion_count": 2,
	"suggestions": [
		{
			"rule_id": "PY001",
			"title": "Prefer direct iteration over range(len())",
			"impact": "medium",
			"confidence": 0.84,
			"language": "python"
		}
	]
}
```

Interpretation:
- `rule_id` identifies the optimization heuristic that fired.
- `impact` is an estimated optimization potential (`low|medium|high`).
- `confidence` is the rule confidence score (`0.0` to `1.0`).
- This is intentionally deterministic for MVP and will later be augmented by local LLM proposals.

### 8) `ecocode optimize patch`

Command:

```bash
ecocode optimize patch path/to/script.py --json
```

Example JSON excerpt:

```json
{
	"schemaVersion": 1,
	"command": "optimize patch",
	"script": "/workspace/path/to/script.py",
	"candidate_path": "/workspace/path/to/script.candidate.py",
	"rule_id": "PY001",
	"strategy_title": "Prefer direct iteration over range(len())",
	"applied": true,
	"changes_count": 1
}
```

Interpretation:
- Generates a candidate file that applies one selected deterministic strategy.
- Use `--rule-id` to force a specific rule and `--output` to control destination path.
- Current MVP patch engine is conservative and Python-focused.

### 9) `ecocode optimize evaluate`

Command:

```bash
ecocode optimize evaluate --baseline .ecocode/baseline.json --candidate path/to/candidate.py --json
```

Example JSON excerpt:

```json
{
	"schemaVersion": 1,
	"command": "optimize evaluate",
	"baseline_energy_wh": 0.3442,
	"candidate_energy_wh": 0.331,
	"increase_pct": -3.835,
	"regression": false,
	"status": "passed"
}
```

Interpretation:
- This command verifies whether a generated/refactored candidate improves or regresses versus baseline.
- `regression=true` returns exit code `2`.
- With `--fail-on-unstable`, unstable measurements return exit code `3`.

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
│   │   ├── optimize.py
│   │   ├── profile.py
│   │   ├── profile_repo.py
│   │   └── trend.py
│   └── core/
│       ├── benchmark.py
│       ├── config.py
│       ├── history.py
│       ├── optimizer.py
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

If you run into bugs, spot potential fixes, or have feature ideas, you are encouraged to open an issue or submit a PR.
