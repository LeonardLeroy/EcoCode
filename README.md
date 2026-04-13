# EcoCode

EcoCode is an open-source toolkit to measure the energy impact of your code, detect regressions, and guide more efficient optimizations.

## What this project is for?

EcoCode helps answer very practical questions:
- Is this script consuming more than before?
- Is a PR degrading performance and energy usage?
- Which files or code areas are the most expensive?
- Which optimizations should be prioritized first?

In practice, the CLI already lets you:
- profile a script (CPU, memory, estimated energy),
- create a baseline and compare future runs,
- scan an entire repository,
- track trends over time,
- generate optimization suggestions,
- export results for CI tooling (JSON/SARIF).

## Why it is useful?

The project makes an often invisible topic visible: the runtime cost of software.

In a team workflow, this makes it easier to:
- compare changes with real numbers instead of guesswork,
- catch energy regressions before they reach production,
- add energy checks to CI the same way we already gate tests and linting,
- improve performance and reliability without losing sight of sustainability.

## Where we are going?

The goal is to become a reference platform for sustainable software engineering:
- increasingly reliable, cross-platform runtime measurement,
- deeper repository analysis,
- smarter optimization recommendations,
- simpler integration into team workflows.

## Full documentation

If you want full details (commands, outputs, examples, roadmap, etc.), see the complete project documentation:

[documentation.md](documentation.md)

## Contributing

If the project interests you and you want to help:

You can:
- propose new features,
- add new functionality,
- fix potential issues and bugs,
- improve the app's reliability,
- submit pull requests.

See also:
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
