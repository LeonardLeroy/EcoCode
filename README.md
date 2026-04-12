# EcoCode

EcoCode is an open-source toolkit to measure, analyze, and optimize software energy consumption.

The project starts with a robust CLI core and expands toward workflow integrations, cloud auditing, and later local AI-assisted refactoring.

## Vision

- Build practical tooling for Green IT and sustainable software engineering.
- Make energy impact visible in local development and CI pipelines.
- Provide a contributor-friendly ecosystem with clear milestones.

## Current Status

Phase 1 has started with a first functional Python CLI prototype.

- Command available: `ecocode profile <script>`
- Output modes: human-readable and JSON (`--json`)
- Scope: deterministic placeholder metrics, ready to be replaced by real runtime collectors

## Repository Structure

```text
.
├── .github/ISSUE_TEMPLATE/
├── docs/
│   └── ROADMAP.md
├── implementations/
│   ├── cpp/
│   ├── csharp/
│   └── rust/
├── src/ecocode/
│   ├── cli.py
│   ├── commands/
│   └── core/
├── tests/
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
```

Run tests:

```bash
pytest
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
