# EcoCode Roadmap

## Current Delivery Snapshot

- Done: `ecocode profile <script>` with text and JSON output.
- Done: `ecocode baseline create` and `ecocode baseline compare`.
- Done: `ecocode profile-repo --root <path>` for repository-wide aggregation.
- Next: replace placeholder metrics with real runtime collectors.

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
3. Add JSON schema for profile report.
4. Add CSV export.
5. Implement repeated-run median profile mode.
6. Add process tree profiling for subprocess-heavy scripts.
7. Add configurable sampling interval.
8. Add project-level config file (`ecocode.toml`).
9. Add include/exclude path filters.
10. Add Windows-specific process collector.
11. Add Linux cgroup-aware measurements.
12. Add macOS collector.
13. Add deterministic benchmark fixture pack.
14. Add SARIF output for CI tooling.
15. Add GitHub Action prototype.
16. Add static rules engine skeleton.
17. Add VS Code extension MVP (display profile report).
18. Add plugin protocol between CLI and IDE.
19. Add telemetry policy document (opt-in).
20. Add release automation and signed artifacts.
