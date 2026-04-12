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
- GitHub Action prototype for `profile-repo` with SARIF publication.
- `schemaVersion` policy with compatibility tests for JSON payloads.

### In Progress

- Calibration and stability hardening (configurable factors and thresholds are in place).
- Runtime collector quality improvements for cross-platform parity.

### Next

- Benchmark noise-control profiles and acceptance thresholds.

## Priority Issues

1. Add benchmark noise-control profiles (idle/warm/cpu-bound) and acceptance thresholds.
2. Add configurable sampling interval for runtime collectors.
3. Add macOS process-tree-aware runtime collector path.
4. Add static rules engine skeleton for early anti-pattern checks.
5. Add baseline/result migration helpers for future schema upgrades.

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
