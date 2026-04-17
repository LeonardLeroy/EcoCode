import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import * as path from "node:path";
import { promisify } from "node:util";
import * as vscode from "vscode";
import { CollectorType, EcoCodeRepoReport, EcoCodeScriptReport } from "./types";

const execFileAsync = promisify(execFile);

interface ExtensionSettings {
  cliPath: string;
  collector: CollectorType;
  maxFiles: number;
  runs: number;
  extensions: string[];
  includeGlobs: string[];
  excludeGlobs: string[];
  autoRefreshSeconds: number;
  showTopFiles: number;
  liveModeEnabled: boolean;
  liveScope: "workspace" | "file" | "both";
}

function ensureNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return fallback;
}

function ensureStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

export function loadSettings(): ExtensionSettings {
  const config = vscode.workspace.getConfiguration("ecocode");
  return {
    cliPath: config.get<string>("cliPath", "ecocode"),
    collector: config.get<CollectorType>("collector", "placeholder"),
    maxFiles: Math.max(1, ensureNumber(config.get("maxFiles"), 200)),
    runs: Math.max(1, ensureNumber(config.get("runs"), 1)),
    extensions: ensureStringArray(config.get("extensions")),
    includeGlobs: ensureStringArray(config.get("includeGlobs")),
    excludeGlobs: ensureStringArray(config.get("excludeGlobs")),
    autoRefreshSeconds: Math.max(10, ensureNumber(config.get("autoRefreshSeconds"), 20)),
    showTopFiles: Math.max(1, ensureNumber(config.get("showTopFiles"), 15)),
    liveModeEnabled: config.get<boolean>("liveModeEnabled", true),
    liveScope: config.get<"workspace" | "file" | "both">("liveScope", "both"),
  };
}

interface EcoCodeExecutionTarget {
  command: string;
  baseArgs: string[];
}

async function exists(filePath: string): Promise<boolean> {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function resolveExecutionTarget(cliPath: string, cwd: string): Promise<EcoCodeExecutionTarget> {
  const normalizedCliPath = cliPath.trim();

  if (normalizedCliPath.length > 0 && normalizedCliPath !== "ecocode") {
    return { command: normalizedCliPath, baseArgs: [] };
  }

  const unixCli = path.join(cwd, ".venv", "bin", "ecocode");
  if (await exists(unixCli)) {
    return { command: unixCli, baseArgs: [] };
  }

  const winCli = path.join(cwd, ".venv", "Scripts", "ecocode.exe");
  if (await exists(winCli)) {
    return { command: winCli, baseArgs: [] };
  }

  const unixPython = path.join(cwd, ".venv", "bin", "python");
  if (await exists(unixPython)) {
    return { command: unixPython, baseArgs: ["-m", "ecocode.cli"] };
  }

  const winPython = path.join(cwd, ".venv", "Scripts", "python.exe");
  if (await exists(winPython)) {
    return { command: winPython, baseArgs: ["-m", "ecocode.cli"] };
  }

  return { command: "ecocode", baseArgs: [] };
}

function parseJsonFromOutput(output: string): unknown {
  const trimmed = output.trim();
  if (trimmed.length === 0) {
    throw new Error("EcoCode produced empty output.");
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(trimmed.slice(start, end + 1));
    }
    throw new Error("Unable to parse EcoCode JSON output.");
  }
}

async function runEcoCode(cliPath: string, args: string[], cwd: string): Promise<string> {
  try {
    const target = await resolveExecutionTarget(cliPath, cwd);
    const { stdout, stderr } = await execFileAsync(target.command, [...target.baseArgs, ...args], {
      cwd,
      timeout: 120000,
      maxBuffer: 5 * 1024 * 1024,
      windowsHide: true,
    });
    if (stderr && stderr.trim().length > 0) {
      // EcoCode may print non-fatal info on stderr in some environments.
    }
    return stdout;
  } catch (error) {
    const maybe = error as { stdout?: string; stderr?: string; message?: string; code?: string };
    if (maybe.code === "ENOENT") {
      throw new Error(
        "EcoCode CLI not found. Set ecocode.cliPath or create .venv with EcoCode installed (for example: .venv/bin/ecocode).",
      );
    }
    const details = (maybe.stderr || maybe.stdout || maybe.message || "Unknown EcoCode execution error").trim();
    throw new Error(details);
  }
}

export async function profileWorkspace(rootPath: string): Promise<EcoCodeRepoReport> {
  const settings = loadSettings();
  const args = [
    "profile-repo",
    "--root",
    rootPath,
    "--collector",
    settings.collector,
    "--max-files",
    String(settings.maxFiles),
    "--runs",
    String(settings.runs),
    "--json",
  ];

  for (const ext of settings.extensions) {
    args.push("--ext", ext);
  }
  for (const glob of settings.includeGlobs) {
    args.push("--include-glob", glob);
  }
  for (const glob of settings.excludeGlobs) {
    args.push("--exclude-glob", glob);
  }

  const stdout = await runEcoCode(settings.cliPath, args, rootPath);
  const parsed = parseJsonFromOutput(stdout);
  return parsed as EcoCodeRepoReport;
}

export async function profileScript(scriptPath: string, workspacePath: string): Promise<EcoCodeScriptReport> {
  const settings = loadSettings();
  const args = [
    "profile",
    scriptPath,
    "--collector",
    settings.collector,
    "--runs",
    String(settings.runs),
    "--json",
  ];

  const stdout = await runEcoCode(settings.cliPath, args, workspacePath);
  const parsed = parseJsonFromOutput(stdout);
  return parsed as EcoCodeScriptReport;
}
