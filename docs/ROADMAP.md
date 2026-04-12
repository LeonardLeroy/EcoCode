# EcoCode Roadmap

## Status Board

### Done

- Core CLI commands: `profile`, `baseline create/compare`, `profile-repo`, `trend`.
- Output channels: human-readable, JSON, CSV (trend), SARIF (repo profiling).
- Runtime collector preview on Linux/Unix with subprocess-aware process-group sampling.
- Repeated-run mode with median/stddev/CV and stability gates.
- Include/exclude glob filters for repository profiling.
- Local run history and trend progression.
- Reliability suite expanded (contracts, aggregation, properties, runtime behavior).
- JSON schema validation enforced for `profile`, `baseline compare`, `profile-repo`, and `trend` outputs.
- Benchmark reproducibility runner with fixture pack (`ecocode benchmark`).
- Windows runtime collector backend preview.
- Linux cgroup-aware measurements for runtime collector (container-aware memory path).
- Runtime collector sampling interval exposed through CLI and core profiler APIs.
- GitHub Action prototype for `profile-repo` with SARIF publication.
- `schemaVersion` policy with compatibility tests for JSON payloads.
- Benchmark noise profiles (`idle`, `warm`, `cpu-bound`) and acceptance thresholds.
- Optimizer MVP started with `ecocode optimize suggest` (rule-based deterministic mode).
- Optimizer MVP includes `ecocode optimize patch` (deterministic candidate generation, Python-focused MVP).
- Optimizer MVP includes `ecocode optimize evaluate` (candidate vs baseline regression gates).
- Repository audit defaults expanded for major languages (Python, C/C++, C#, Rust, JS/TS, HTML/CSS, Assembly).

### In Progress

- Calibration and stability hardening (configurable factors and thresholds are in place).
- Runtime collector quality improvements for cross-platform parity.

### Next

- Expand Optimizer patch strategy coverage beyond initial Python-safe rules.

## Priority Issues

1. Prepare local LLM integration path (model runner abstraction + prompt contracts).
2. Add team-level optimization policy in config (`optimize` section with accepted risk/quality gates).
3. Add language-specific optimization rule packs (Python/C++/Rust/JS/C#/HTML-CSS/ASM).
4. Expand deterministic patch strategies and safety checks for multi-language candidates.

## Current Delivery Snapshot

- Done: `ecocode profile <script>` with text and JSON output.
- Done: `ecocode baseline create` and `ecocode baseline compare`.
- Done: `ecocode profile-repo --root <path>` for repository-wide aggregation.
- Done: `ecocode trend` to summarize audit progression history.
- Done: SARIF export support via `profile-repo --sarif-output`.
- Done: project configuration support through `ecocode.toml`.
- Done: extended reliability suite (contracts, aggregation, and property tests).
- Done: Linux/Unix runtime collector preview (`--collector runtime`).
- Done: Windows runtime collector preview (`--collector runtime`).
- Done: repeated-run profiling mode (`--runs`) with median/stddev summaries.
- Done: Linux process-group sampling for subprocess-aware runtime profiling.
- Done: Linux cgroup-aware memory sampling for containerized runtime contexts.
- Done: GitHub Action prototype to run `profile-repo` and upload SARIF.
- Done: `schemaVersion` policy and compatibility tests for JSON outputs.
- Done: benchmark noise profiles and acceptance threshold gating.
- Done: calibration/stability config hooks (`[calibration]`, `[stability]`).
- Next: benchmark reproducibility hardening (noise controls + acceptance profiles) and external metrology validation.

## Phase 1 - The Core

- CLI command set (`profile`, `baseline`, `compare`, `report`).
- Runtime sampling for CPU, memory, wall time.
- Initial energy estimation model with calibration profiles.
- Multi-platform support: Linux and Windows first, macOS next.
- Export formats: JSON, SARIF, Markdown.
- Baseline snapshots for regression detection.

## Phase 2 - Workflow Integration

- Static linter for common energy anti-patterns.
- GitHub Action with PR annotations and quality gates.
- Optional pre-commit integration.
- IDE surfaces (VS Code extension) for local feedback.

## Phase 3 - Cloud and Infrastructure

- Docker image audit (size, layers, startup overhead).
- Kubernetes manifest checks for wasteful defaults.
- Infrastructure scorecards for cloud deployment decisions.
- Cost + CO2 approximation per service profile.

## Phase 4 - Local AI Refactoring

- Local SLM assistant for optimization suggestions.
- Explainable recommendations with confidence and trade-offs.
- Safety constraints and reproducible benchmark harness.

### Phase 4.1 - Optimizer MVP (near-term)

- `ecocode optimize suggest <script>`: produce optimization suggestions without code rewrite.
- `ecocode optimize patch <script>`: generate candidate patch from selected strategy.
- `ecocode optimize evaluate --baseline <file> --candidate <file>`: benchmark candidate and gate regression.
- Keep deterministic fallback (rule engine) when no local model is configured.
- Persist before/after evidence in JSON for CI review.

### Phase 4.2 - Local LLM Integration

- Add local model provider interface (Ollama/llama.cpp compatible backends).
- Start with small coding models for low VRAM environments, then scale up to larger models when hardware allows.
- Add prompt/test harness to compare candidate quality and ensure reproducibility.

## Platform Focus Note

- macOS runtime collector parity is intentionally deferred for now.
- Active focus remains Linux and Windows collectors plus cross-language static/repository auditing.

## Language Coverage Track

- Current high-priority language targets: Python, C, C++, C#, Rust, JavaScript, HTML/CSS, Assembly.
- Repository audit should keep working even when runtime execution is language-limited.
- Runtime execution remains strongest on Python/executable paths while optimizer and static tracks become language-agnostic.

## Parallel Tracks (cross-phase)

- Language implementations:
  - Python reference implementation (fast iteration).
  - Rust engine for high-performance probes.
  - C++/C# adapters for ecosystem-specific integrations.
- Benchmark corpus and fixtures.
- Documentation, tutorials, and contributor onboarding.
- Governance: maintainers, release process, RFC flow.

## Suggested Milestone Backlog

1. Done: Add `ecocode baseline create` command.
2. Done: Add `ecocode baseline compare` command.
3. Done: Add JSON schema for profile report.
4. Done: Add CSV export.
5. Done: Implement repeated-run median profile mode.
6. Done: Add process tree profiling for subprocess-heavy scripts (Linux preview).
7. Add configurable sampling interval.
8. Done: Add project-level config file (`ecocode.toml`).
9. Done: Add include/exclude path filters.
10. Done: Add Windows-specific process collector (preview).
11. Done: Add Linux cgroup-aware measurements.
12. Add macOS collector.
13. Done: Add deterministic benchmark fixture pack and reproducibility runner (`benchmark`).
14. Done: Add SARIF output for CI tooling.
15. Done: Add GitHub Action prototype.
16. Add static rules engine skeleton.
17. Add VS Code extension MVP (display profile report).
18. Add plugin protocol between CLI and IDE.
19. Add telemetry policy document (opt-in).
20. Add release automation and signed artifacts.
