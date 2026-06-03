# EcoCode

Try the VS Code extension on Marketplace: [EcoCode Insights](https://marketplace.visualstudio.com/items?itemName=ecocode.ecocode-vscode)

[![EcoCode Insights logo](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/Ecocode.png)](https://marketplace.visualstudio.com/items?itemName=ecocode.ecocode-vscode)

EcoCode is an open-source toolkit to measure the energy impact of your code, detect regressions, and guide more efficient optimizations.

## In action

Inline optimization suggestions (squiggles + code actions), a workspace dashboard, and honest "measured vs estimated" labels.

![Optimization suggestions and inline diagnostics](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/screenshots/suggestions.png)

![Workspace summary dashboard](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/screenshots/dashboard.png)

![Top files with measured/estimated badges](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/screenshots/top-files.png)

![Current file metrics](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/screenshots/current-file.png)

![Stability panel](https://raw.githubusercontent.com/LeonardLeroy/EcoCode/main/vscode-extension/media/screenshots/stability.png)

## Install

```bash
pip install ecocode-cli
```

This installs the `ecocode` command (Python 3.10+). A few examples:

```bash
ecocode profile path/to/script.py            # profile a single file
ecocode profile-repo --root .                # scan a whole repository
ecocode optimize suggest path/to/script.py   # optimization suggestions
```

Prefer a GUI? Install the [VS Code extension](https://marketplace.visualstudio.com/items?itemName=ecocode.ecocode-vscode) — it drives the same CLI.

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

## AI suggestions are optional

EcoCode works fully offline with deterministic, rule-based suggestions — **no API key needed**. AI-powered suggestions are opt-in, configured in `ecocode.toml`:

- **Local (Ollama):** a model runs on your machine; your code never leaves it; no key. The endpoint is configurable via `ECOCODE_OLLAMA_BASE_URL` (HTTP or HTTPS).
- **Remote (Anthropic):** higher quality, but your source is sent to the API, so it needs **your own** key via the `ECOCODE_LLM_API_KEY` environment variable. The key is read **only** from the environment — never stored in `ecocode.toml`, VS Code settings, or the repository.

```bash
export ECOCODE_LLM_API_KEY="sk-ant-..."   # only needed for the remote provider
```

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
