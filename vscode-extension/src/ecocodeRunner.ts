import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { promisify } from "node:util";
import * as vscode from "vscode";
import {
  CollectorType,
  EcoCodePatchReport,
  EcoCodeRepoReport,
  EcoCodeScriptReport,
  EcoCodeSuggestReport,
} from "./types";

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
  diagnosticsEnabled: boolean;
  timeoutSeconds: number;
  installSource: string;
}

let runnerLogger: ((message: string) => void) | undefined;

export function setRunnerLogger(logger: (message: string) => void): void {
  runnerLogger = logger;
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
    cliPath: config.get<string>("cliPath", ""),
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
    diagnosticsEnabled: config.get<boolean>("diagnosticsEnabled", true),
    timeoutSeconds: Math.max(5, ensureNumber(config.get("timeoutSeconds"), 120)),
    installSource: config.get<string>("installSource", "ecocode-cli"),
  };
}

export function getGlobalInstallRoot(): string {
  const configuredRoot = process.env.ECOCODE_HOME?.trim();
  if (configuredRoot) {
    return configuredRoot;
  }

  if (process.platform === "win32") {
    const appData = process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
    return path.join(appData, "EcoCode");
  }

  const xdgDataHome = process.env.XDG_DATA_HOME?.trim();
  if (xdgDataHome) {
    return path.join(xdgDataHome, "ecocode");
  }

  return path.join(os.homedir(), ".local", "share", "ecocode");
}

export function getGlobalCliPath(): string {
  const root = getGlobalInstallRoot();
  if (process.platform === "win32") {
    return path.join(root, "venv", "Scripts", "ecocode.exe");
  }
  return path.join(root, "venv", "bin", "ecocode");
}

export function getGlobalPythonPath(): string {
  const root = getGlobalInstallRoot();
  if (process.platform === "win32") {
    return path.join(root, "venv", "Scripts", "python.exe");
  }
  return path.join(root, "venv", "bin", "python");
}

export function getPipxCliPath(): string {
  const binDir = process.env.PIPX_BIN_DIR?.trim() || path.join(os.homedir(), ".local", "bin");
  if (process.platform === "win32") {
    return path.join(binDir, "ecocode.exe");
  }
  return path.join(binDir, "ecocode");
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

  const globalCliPath = getGlobalCliPath();
  if (await exists(globalCliPath)) {
    return { command: globalCliPath, baseArgs: [] };
  }

  const pipxCli = getPipxCliPath();
  if (await exists(pipxCli)) {
    return { command: pipxCli, baseArgs: [] };
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
  const timeoutSeconds = loadSettings().timeoutSeconds;
  try {
    const target = await resolveExecutionTarget(cliPath, cwd);
    const { stdout, stderr } = await execFileAsync(target.command, [...target.baseArgs, ...args], {
      cwd,
      timeout: timeoutSeconds * 1000,
      maxBuffer: 5 * 1024 * 1024,
      windowsHide: true,
    });
    if (stderr && stderr.trim().length > 0) {
      // Non-fatal diagnostics from the CLI are useful for troubleshooting.
      runnerLogger?.(`EcoCode stderr: ${stderr.trim()}`);
    }
    return stdout;
  } catch (error) {
    const maybe = error as {
      stdout?: string;
      stderr?: string;
      message?: string;
      code?: string;
      killed?: boolean;
      signal?: string;
    };
    if (maybe.code === "ENOENT") {
      throw new Error(
        `EcoCode CLI not found. Run EcoCode: Setup CLI once to install it globally at ${getGlobalCliPath()} or set ecocode.cliPath to a valid executable path.`,
      );
    }
    if (maybe.killed || maybe.signal === "SIGTERM") {
      throw new Error(
        `EcoCode timed out after ${timeoutSeconds}s. Increase ecocode.timeoutSeconds or reduce ecocode.maxFiles for large workspaces.`,
      );
    }
    const details = (maybe.stderr || maybe.stdout || maybe.message || "Unknown EcoCode execution error").trim();
    throw new Error(details);
  }
}

export const GIT_INSTALL_FALLBACK = "git+https://github.com/LeonardLeroy/EcoCode.git";

export interface CliInstallResult {
  method: "pipx" | "venv";
  cliPath: string;
}

async function commandResponds(command: string, args: string[]): Promise<boolean> {
  try {
    await execFileAsync(command, args, { timeout: 8000, windowsHide: true });
    return true;
  } catch {
    return false;
  }
}

/**
 * Cheap presence check: look at the known install locations first and only fall
 * back to spawning a process when none of them match.
 */
export async function isCliAvailable(cwd: string): Promise<boolean> {
  const configured = loadSettings().cliPath.trim();
  if (configured.length > 0 && configured !== "ecocode") {
    return exists(configured);
  }

  const isWindows = process.platform === "win32";
  const candidates = [
    getGlobalCliPath(),
    getPipxCliPath(),
    isWindows
      ? path.join(cwd, ".venv", "Scripts", "ecocode.exe")
      : path.join(cwd, ".venv", "bin", "ecocode"),
    isWindows
      ? path.join(cwd, ".venv", "Scripts", "python.exe")
      : path.join(cwd, ".venv", "bin", "python"),
  ];

  for (const candidate of candidates) {
    if (await exists(candidate)) {
      return true;
    }
  }

  return commandResponds("ecocode", ["--version"]);
}

async function findSystemPython(): Promise<string[] | undefined> {
  const candidates: string[][] = process.platform === "win32"
    ? [["py", "-3"], ["python"], ["python3"]]
    : [["python3"], ["python"]];

  for (const candidate of candidates) {
    if (await commandResponds(candidate[0], [...candidate.slice(1), "--version"])) {
      return candidate;
    }
  }
  return undefined;
}

/**
 * Install the CLI without opening a terminal.
 *
 * Order matters for speed: pipx reuses its own shared base and is PEP 668-safe,
 * so it is tried first. The venv path deliberately skips `pip install -U pip`
 * (a full extra download that buys nothing here) and forces wheels so pip never
 * falls back to building a source distribution.
 */
export async function installCliHeadless(
  log: (message: string) => void,
  token?: vscode.CancellationToken,
): Promise<CliInstallResult> {
  const installSource = loadSettings().installSource.trim() || "ecocode-cli";
  const sources = installSource === GIT_INSTALL_FALLBACK
    ? [installSource]
    : [installSource, GIT_INSTALL_FALLBACK];

  const run = async (command: string, args: string[]): Promise<void> => {
    if (token?.isCancellationRequested) {
      throw new Error("EcoCode CLI installation cancelled.");
    }
    log(`$ ${command} ${args.join(" ")}`);
    const { stdout, stderr } = await execFileAsync(command, args, {
      timeout: 10 * 60 * 1000,
      maxBuffer: 10 * 1024 * 1024,
      windowsHide: true,
    });
    const output = `${stdout ?? ""}${stderr ?? ""}`.trim();
    if (output.length > 0) {
      log(output);
    }
  };

  const pipFlags = ["--disable-pip-version-check", "--no-input"];
  const errors: string[] = [];

  if (await commandResponds("pipx", ["--version"])) {
    for (const source of sources) {
      try {
        await run("pipx", ["install", source]);
        return { method: "pipx", cliPath: getPipxCliPath() };
      } catch (error) {
        errors.push(`pipx install ${source}: ${(error as Error).message}`);
      }
    }
  }

  const python = await findSystemPython();
  if (!python) {
    throw new Error(
      `No Python 3.10+ interpreter found on PATH. Install Python, then run EcoCode: Setup CLI. (${errors.join(" | ")})`,
    );
  }

  const venvPath = path.join(getGlobalInstallRoot(), "venv");
  const venvPython = getGlobalPythonPath();

  if (!(await exists(venvPython))) {
    await run(python[0], [...python.slice(1), "-m", "venv", venvPath]);
  }

  for (const source of sources) {
    // Wheel-only first: a source build is what makes a git install slow.
    const attempts = [
      [...pipFlags, "--only-binary=:all:", "-U", source],
      [...pipFlags, "-U", source],
    ];
    for (const attempt of attempts) {
      try {
        await run(venvPython, ["-m", "pip", "install", ...attempt]);
        return { method: "venv", cliPath: getGlobalCliPath() };
      } catch (error) {
        errors.push(`pip install ${source}: ${(error as Error).message}`);
      }
    }
  }

  throw new Error(`EcoCode CLI installation failed. ${errors.join(" | ")}`);
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
  let runsForFile = settings.runs;
  if (runsForFile < 2) {
    runsForFile = 3;
  }

  const args = [
    "profile",
    scriptPath,
    "--collector",
    settings.collector,
    "--runs",
    String(runsForFile),
    "--json",
  ];

  const stdout = await runEcoCode(settings.cliPath, args, workspacePath);
  const parsed = parseJsonFromOutput(stdout);
  return parsed as EcoCodeScriptReport;
}

export async function getOptimizationSuggestions(
  scriptPath: string,
  workspacePath: string,
  includeLlm = false,
): Promise<EcoCodeSuggestReport> {
  const settings = loadSettings();
  const args = ["optimize", "suggest", scriptPath, "--json"];
  if (!includeLlm) {
    // Keep editor diagnostics fast and deterministic; LLM stays opt-in.
    args.push("--no-llm");
  }
  const stdout = await runEcoCode(settings.cliPath, args, workspacePath);
  const parsed = parseJsonFromOutput(stdout);
  return parsed as EcoCodeSuggestReport;
}

export async function generateOptimizationPatch(
  scriptPath: string,
  ruleId: string | undefined,
  workspacePath: string,
  useLlm: boolean,
): Promise<EcoCodePatchReport> {
  const settings = loadSettings();
  const args = ["optimize", "patch", scriptPath, "--overwrite", "--json"];
  if (ruleId) {
    args.push("--rule-id", ruleId);
  }
  if (useLlm) {
    args.push("--use-llm");
  }
  const stdout = await runEcoCode(settings.cliPath, args, workspacePath);
  const parsed = parseJsonFromOutput(stdout);
  return parsed as EcoCodePatchReport;
}
