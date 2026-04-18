# EcoCode Insights VS Code Extension

EcoCode Insights is a VS Code extension that runs EcoCode CLI scans and displays repository performance, energy/runtime metrics in a dashboard.

## Demo

![EcoCode Insights demo](media/EcocodeGIF.gif)

## Important

The extension requires EcoCode CLI to be available. If needed, set `ecocode.cliPath` to the absolute executable path.
See this repo: https://github.com/LeonardLeroy/EcoCode

## Features

- Scan whole workspace with EcoCode CLI.
- Scan currently opened file.
- Auto refresh scans on interval.
- Show summary, stability, top files, and current-file metrics.
- Configure scan filters directly from command palette.

## Commands

- `EcoCode: Open Dashboard`
- `EcoCode: Scan Workspace`
- `EcoCode: Scan Current File`
- `EcoCode: Start Auto Refresh`
- `EcoCode: Stop Auto Refresh`
- `EcoCode: Configure Scan Filters`

## Settings

- `ecocode.cliPath`: path to `ecocode` executable.
- `ecocode.collector`: `placeholder` or `runtime`.
- `ecocode.maxFiles`: max number of scanned files.
- `ecocode.runs`: repeated runs for stability.
- `ecocode.extensions`: optional extension filters.
- `ecocode.includeGlobs`: optional include globs.
- `ecocode.excludeGlobs`: optional exclude globs.
- `ecocode.autoRefreshSeconds`: auto refresh interval.
- `ecocode.showTopFiles`: max files shown in dashboard table.

## Local Development

```bash
cd vscode-extension
npm install
npm run compile
```