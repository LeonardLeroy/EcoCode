import * as vscode from "vscode";
import * as os from "node:os";
import * as path from "node:path";
import { getDashboardHtml } from "./dashboard";
import {
  generateOptimizationPatch,
  getGlobalInstallRoot,
  getGlobalPythonPath,
  loadSettings,
  profileScript,
  profileWorkspace,
  setRunnerLogger,
} from "./ecocodeRunner";
import { EcoCodeCodeActionProvider, EcoCodeSuggestionManager, isSupportedDocument } from "./suggestions";
import { DashboardState, EcoCodeSuggestReport } from "./types";

class EcoCodeController implements vscode.WebviewViewProvider {
  private view: vscode.WebviewView | undefined;
  private readonly output = vscode.window.createOutputChannel("EcoCode Insights");
  private readonly statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  private liveTimer: NodeJS.Timeout | undefined;
  private workspaceScanInFlight = false;
  private fileScanInFlight = false;
  private cliMissingPromptShown = false;
  private schemaWarningShown = false;
  private static readonly supportedSchemaVersion = 1;
  private readonly suggestionManager: EcoCodeSuggestionManager;
  //private dotTimer: NodeJS.Timeout | undefined;

  private state: DashboardState = {
    updatedAtIso: new Date(0).toISOString(),
    autoRefreshActive: false,
    autoRefreshSeconds: loadSettings().autoRefreshSeconds,
    showTopFiles: loadSettings().showTopFiles,
  };

  constructor(private readonly context: vscode.ExtensionContext) {
    this.statusBar.command = "ecocode.openDashboard";
    this.statusBar.tooltip = "Focus EcoCode Insights view";
    this.updateStatusBar();
    this.statusBar.show();

    this.context.subscriptions.push(this.output, this.statusBar);
    setRunnerLogger((message) => this.log(message));

    this.suggestionManager = new EcoCodeSuggestionManager(
      (uri) => this.getWorkspaceRoot(uri)?.fsPath,
      (message) => this.log(message),
      (uri, report) => this.handleSuggestionReport(uri, report),
    );
    this.context.subscriptions.push(this.suggestionManager);

    this.context.subscriptions.push(
      vscode.languages.registerCodeActionsProvider(
        { language: "python", scheme: "file" },
        new EcoCodeCodeActionProvider(),
        { providedCodeActionKinds: EcoCodeCodeActionProvider.providedCodeActionKinds },
      ),
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
          this.suggestionManager.scheduleRefresh(editor.document, 200);
        }
      }),
      vscode.workspace.onDidSaveTextDocument((document) => {
        this.suggestionManager.scheduleRefresh(document, 200);
      }),
      vscode.workspace.onDidChangeTextDocument((event) => {
        if (vscode.window.activeTextEditor?.document === event.document) {
          this.suggestionManager.scheduleRefresh(event.document);
        }
      }),
      vscode.workspace.onDidCloseTextDocument((document) => {
        this.suggestionManager.clear(document.uri);
      }),
    );

    if (vscode.window.activeTextEditor) {
      this.suggestionManager.scheduleRefresh(vscode.window.activeTextEditor.document, 1500);
    }

    this.context.subscriptions.push(
      //   vscode.window.onDidChangeActiveTextEditor(() => {
      //     const settings = loadSettings();
      //     if (!settings.liveModeEnabled) {
      //       return;
      //     }
      //     if (settings.liveScope === "file" || settings.liveScope === "both") {
      //       void this.scanCurrentFile(false);
      //     }
      //   }),
      //   vscode.workspace.onDidSaveTextDocument((document) => {
      //     const settings = loadSettings();
      //     if (!settings.liveModeEnabled) {
      //       return;
      //     }
      //     const activeEditor = vscode.window.activeTextEditor;
      //     if (!activeEditor || activeEditor.document.uri.toString() !== document.uri.toString()) {
      //       return;
      //     }
      //     if (settings.liveScope === "file" || settings.liveScope === "both") {
      //       void this.scanCurrentFile(false);
      //     }
      //   }),
    );

    this.context.subscriptions.push(
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("ecocode")) {
          const settings = loadSettings();
          this.state.autoRefreshSeconds = settings.autoRefreshSeconds;
          this.state.showTopFiles = settings.showTopFiles;
          if (this.state.autoRefreshActive) {
            this.stopLiveMode(false);
            this.startLiveMode(false);
          }
          this.pushState();
        }
      }),
    );

    const initialSettings = loadSettings();
    if (initialSettings.liveModeEnabled && vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
      // Delay slightly so the webview has time to register before the first scan notification fires
      setTimeout(() => {
        this.startLiveMode(false);
      }, 2000);
    }
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    this.view.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.context.extensionUri],
    };
    this.view.webview.html = getDashboardHtml(this.view.webview, this.context.extensionUri);

    this.view.webview.onDidReceiveMessage(async (message) => {
      if (message?.type === "ready") {
        this.pushState();
        return;
      }
      if (message?.type === "scanWorkspace") {
        await this.scanWorkspace();
        return;
      }
      if (message?.type === "scanCurrentFile") {
        await this.scanCurrentFile();
      }
    });

    this.view.onDidDispose(() => {
      this.view = undefined;
    });

    this.pushState();
  }

  async focusDashboard(): Promise<void> {
    await vscode.commands.executeCommand("workbench.view.explorer");
    try {
      await vscode.commands.executeCommand("ecocode.insightsView.focus");
    } catch {
      // Focus command may not be available until view is initialized.
    }
  }

  async scanWorkspace(showFeedback = true): Promise<void> {
    if (this.workspaceScanInFlight) {
      return;
    }

    const workspaceRoot = this.getWorkspaceRoot();
    if (!workspaceRoot) {
      vscode.window.showWarningMessage("Open a workspace folder before scanning.");
      return;
    }

    this.workspaceScanInFlight = true;
    //this.startScanningUI("workspace");

    try {
      let report!: import("./types").EcoCodeRepoReport;
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Window,
          title: "EcoCode",
          cancellable: false,
        },
        async (progress) => {
          progress.report({ message: "Scanning workspace…" });
          report = await profileWorkspace(workspaceRoot.fsPath);
        },
      );

      this.state.workspaceReport = report;
      this.state.updatedAtIso = new Date().toISOString();
      this.state.lastError = undefined;
      this.cliMissingPromptShown = false;
      this.checkSchemaVersion(report.schemaVersion);
      this.log("Workspace scan complete.");
      this.updateStatusBar();
      if (showFeedback) {
        vscode.window.showInformationMessage(
          `EcoCode scan complete: ${report.total_files} files, ${report.total_energy_wh} Wh`,
        );
      }
    } catch (error) {
      const message = this.errorMessage(error);
      this.state.lastError = message;
      this.state.updatedAtIso = new Date().toISOString();
      this.log(`Workspace scan failed: ${message}`);
      if (showFeedback) {
        await this.showScanError("workspace", message);
      }
    } finally {
      //this.endScanningUI();
      this.workspaceScanInFlight = false;
      this.pushState();
    }
  }

  async scanCurrentFile(showFeedback = true): Promise<void> {
    if (this.fileScanInFlight) {
      return;
    }

    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      if (showFeedback) {
        vscode.window.showInformationMessage("Open a file before running current file scan.");
      }
      return;
    }

    const workspaceRoot = this.getWorkspaceRoot(editor.document.uri);
    if (!workspaceRoot) {
      vscode.window.showWarningMessage("Current file is not inside an open workspace folder.");
      return;
    }

    this.fileScanInFlight = true;
    //this.startScanningUI("file");

    try {
      let report!: import("./types").EcoCodeScriptReport;
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Window,
          title: "EcoCode",
          cancellable: false,
        },
        async (progress) => {
          progress.report({ message: "Scanning file…" });
          report = await profileScript(editor.document.uri.fsPath, workspaceRoot.fsPath);
        },
      );

      this.state.scriptReport = report;
      this.state.updatedAtIso = new Date().toISOString();
      this.state.lastError = undefined;
      this.cliMissingPromptShown = false;
      this.checkSchemaVersion(report.schemaVersion);
      this.log(`Current file scan complete: ${report.script}`);
      this.updateStatusBar();
      if (showFeedback) {
        vscode.window.showInformationMessage(
          `EcoCode file scan complete: ${report.estimated_energy_wh} Wh (${report.sustainability_score}/100)`,
        );
      }
    } catch (error) {
      const message = this.errorMessage(error);
      this.state.lastError = message;
      this.state.updatedAtIso = new Date().toISOString();
      this.log(`Current file scan failed: ${message}`);
      if (showFeedback) {
        await this.showScanError("file", message);
      }
    } finally {
      //this.endScanningUI();
      this.fileScanInFlight = false;
      this.pushState();
    }
  }

  private handleSuggestionReport(uri: vscode.Uri, report: EcoCodeSuggestReport): void {
    const active = vscode.window.activeTextEditor;
    if (active && active.document.uri.toString() === uri.toString()) {
      this.state.scriptSuggestions = report;
      this.pushState();
    }
  }

  async suggestForFile(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showInformationMessage("Open a file to get EcoCode suggestions.");
      return;
    }
    if (!isSupportedDocument(editor.document)) {
      vscode.window.showInformationMessage("EcoCode has no suggestions for this file type.");
      return;
    }

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Window,
        title: "EcoCode",
        cancellable: false,
      },
      async (progress) => {
        progress.report({ message: "Analyzing for optimizations…" });
        const report = await this.suggestionManager.refresh(editor.document, true);
        if (report) {
          vscode.window.showInformationMessage(
            `EcoCode: ${report.suggestion_count} optimization suggestion(s).`,
          );
        } else {
          vscode.window.showWarningMessage(
            "EcoCode could not analyze this file. See the EcoCode Insights output for details.",
          );
        }
      },
    );
  }

  async applyPatch(scriptPath: string, ruleId: string | undefined, useLlm: boolean): Promise<void> {
    const fileUri = vscode.Uri.file(scriptPath);
    const workspaceRoot = this.getWorkspaceRoot(fileUri)?.fsPath ?? path.dirname(scriptPath);

    try {
      let report!: import("./types").EcoCodePatchReport;
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Window,
          title: "EcoCode",
          cancellable: false,
        },
        async (progress) => {
          progress.report({ message: useLlm ? "Generating candidate (LLM)…" : "Generating fix…" });
          report = await generateOptimizationPatch(scriptPath, ruleId, workspaceRoot, useLlm);
        },
      );

      const candidateUri = vscode.Uri.file(report.candidate_path);
      await vscode.commands.executeCommand(
        "vscode.diff",
        fileUri,
        candidateUri,
        `EcoCode candidate: ${path.basename(scriptPath)} (${report.rule_id})`,
      );

      const choice = await vscode.window.showInformationMessage(
        `EcoCode generated a candidate with ${report.changes_count} change(s): ${report.strategy_title}.`,
        "Apply to file",
        "Keep candidate file",
        "Discard candidate",
      );

      if (choice === "Apply to file") {
        const candidateBytes = await vscode.workspace.fs.readFile(candidateUri);
        await vscode.workspace.fs.writeFile(fileUri, candidateBytes);
        await vscode.workspace.fs.delete(candidateUri);
        vscode.window.showInformationMessage("EcoCode fix applied.");
      } else if (choice === "Discard candidate") {
        await vscode.workspace.fs.delete(candidateUri);
      }
    } catch (error) {
      await this.showScanError("file", this.errorMessage(error));
    }
  }

  async setupCliInWorkspace(): Promise<void> {
    const isWindows = process.platform === "win32";
    const terminal = vscode.window.createTerminal({
      name: "EcoCode Setup",
      cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? os.homedir(),
      // Force PowerShell on Windows: the setup syntax below is PowerShell-specific
      // and cmd.exe would fail on it.
      shellPath: isWindows ? "powershell.exe" : undefined,
      // HISTFILE only makes sense on POSIX shells.
      env: isWindows ? undefined : { HISTFILE: "/tmp/ecocode_setup_history" },
    });

    const globalPythonPath = getGlobalPythonPath();
    const globalInstallRoot = getGlobalInstallRoot();
    const venvPath = path.join(globalInstallRoot, "venv");
    const installSource = loadSettings().installSource;

    const setupCommand = isWindows
      ? [
        `New-Item -ItemType Directory -Force -Path "${globalInstallRoot}" | Out-Null`,
        // py launcher is preferred, but some installs only expose 'python'.
        `if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv "${venvPath}" } else { python -m venv "${venvPath}" }`,
        `& "${globalPythonPath}" -m pip install --upgrade pip`,
        `& "${globalPythonPath}" -m pip install "${installSource}"`,
      ].join("; ")
      : [
        `mkdir -p "${globalInstallRoot}"`,
        `python3 -m venv "${venvPath}"`,
        `"${globalPythonPath}" -m pip install --upgrade pip`,
        `"${globalPythonPath}" -m pip install "${installSource}"`,
      ].join(" && ");

    terminal.show(true);
    terminal.sendText(setupCommand, true);
    vscode.window.showInformationMessage(
      `EcoCode setup started in terminal. Global CLI will be installed at ${
        isWindows
          ? path.join(globalInstallRoot, "venv", "Scripts", "ecocode.exe")
          : path.join(globalInstallRoot, "venv", "bin", "ecocode")
      }.`,
    );
  }

  async showSetupGuide(): Promise<void> {
    const content = [
      "# EcoCode CLI Setup",
      "",
      "EcoCode Insights needs the EcoCode CLI to run scans. This setup only needs to be done once.",
      "",
      "## Quickest (recommended): pipx",
      "",
      "```bash",
      "pipx install ecocode-cli",
      "```",
      "",
      "pipx puts the `ecocode` command on your PATH in its own isolated environment. Requires Python 3.10+.",
      "No pipx? `sudo apt install pipx` (Debian/Ubuntu) or `python3 -m pip install --user pipx`, then `pipx ensurepath`.",
      "",
      "On Debian/Ubuntu/WSL a plain `pip install` into the system Python is blocked (PEP 668) — use pipx or a venv below.",
      "",
      "## Isolated install (virtual environment)",
      "",
      "### Linux / macOS",
      "```bash",
      "python3 -m venv ~/.local/share/ecocode/venv",
      "~/.local/share/ecocode/venv/bin/python -m pip install --upgrade pip",
      "~/.local/share/ecocode/venv/bin/python -m pip install ecocode-cli",
      "```",
      "",
      "### Windows (PowerShell)",
      "```powershell",
      "py -3 -m venv $env:APPDATA\\EcoCode\\venv",
      "$env:APPDATA\\EcoCode\\venv\\Scripts\\python -m pip install --upgrade pip",
      "$env:APPDATA\\EcoCode\\venv\\Scripts\\python -m pip install ecocode-cli",
      "```",
      "",
      "## From GitHub (latest / unreleased)",
      "```bash",
      "pip install \"git+https://github.com/LeonardLeroy/EcoCode.git\"",
      "```",
      "Or set `ecocode.installSource` to this URL to make the Setup button use it.",
      "",
      "## What this gives you",
      "- One global EcoCode CLI for every workspace",
      "- No need to clone the repo just to use the extension",
      "- The extension will auto-detect the global CLI first",
      "",
      "## If CLI is still not detected",
      "Set `ecocode.cliPath` in VS Code settings to the absolute CLI path.",
    ].join("\n");

    const document = await vscode.workspace.openTextDocument({
      language: "markdown",
      content,
    });
    await vscode.window.showTextDocument(document, {
      preview: true,
      viewColumn: vscode.ViewColumn.Beside,
    });
  }

  async configureScanFilters(): Promise<void> {
    const config = vscode.workspace.getConfiguration("ecocode");
    const currentCollector = config.get<string>("collector", "static");
    const currentMaxFiles = config.get<number>("maxFiles", 200);
    const currentRuns = config.get<number>("runs", 1);
    const currentExt = (config.get<string[]>("extensions", []) || []).join(", ");
    const currentInclude = (config.get<string[]>("includeGlobs", []) || []).join(", ");
    const currentExclude = (config.get<string[]>("excludeGlobs", []) || []).join(", ");

    const collector = await vscode.window.showQuickPick(["static", "runtime", "placeholder"], {
      title: "EcoCode collector",
      placeHolder: currentCollector,
    });
    if (!collector) {
      return;
    }

    const maxFilesInput = await vscode.window.showInputBox({
      title: "EcoCode max files",
      prompt: "Maximum files to scan",
      value: String(currentMaxFiles),
      validateInput: (value) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0 ? null : "Enter a number > 0";
      },
    });
    if (!maxFilesInput) {
      return;
    }

    const runsInput = await vscode.window.showInputBox({
      title: "EcoCode runs",
      prompt: "Repeated runs for stability",
      value: String(currentRuns),
      validateInput: (value) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0 ? null : "Enter a number > 0";
      },
    });
    if (!runsInput) {
      return;
    }

    const extInput = await vscode.window.showInputBox({
      title: "EcoCode extensions",
      prompt: "Comma-separated extensions, leave empty for defaults",
      value: currentExt,
    });
    if (extInput === undefined) {
      return;
    }

    const includeInput = await vscode.window.showInputBox({
      title: "EcoCode include globs",
      prompt: "Comma-separated include globs, optional",
      value: currentInclude,
    });
    if (includeInput === undefined) {
      return;
    }

    const excludeInput = await vscode.window.showInputBox({
      title: "EcoCode exclude globs",
      prompt: "Comma-separated exclude globs, optional",
      value: currentExclude,
    });
    if (excludeInput === undefined) {
      return;
    }

    const toArray = (raw: string): string[] =>
      raw
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);

    await config.update("collector", collector, vscode.ConfigurationTarget.Workspace);
    await config.update("maxFiles", Number(maxFilesInput), vscode.ConfigurationTarget.Workspace);
    await config.update("runs", Number(runsInput), vscode.ConfigurationTarget.Workspace);
    await config.update("extensions", toArray(extInput), vscode.ConfigurationTarget.Workspace);
    await config.update("includeGlobs", toArray(includeInput), vscode.ConfigurationTarget.Workspace);
    await config.update("excludeGlobs", toArray(excludeInput), vscode.ConfigurationTarget.Workspace);

    vscode.window.showInformationMessage("EcoCode scan filters updated.");
  }

  startLiveMode(showFeedback = true): void {
    if (this.liveTimer) {
      if (showFeedback) {
        vscode.window.showInformationMessage("EcoCode live mode is already running.");
      }
      return;
    }

    const settings = loadSettings();
    if (!settings.liveModeEnabled) {
      this.state.autoRefreshActive = false;
      this.pushState();
      if (showFeedback) {
        vscode.window.showInformationMessage("EcoCode live mode is disabled in settings.");
      }
      return;
    }

    this.state.autoRefreshSeconds = settings.autoRefreshSeconds;
    this.state.showTopFiles = settings.showTopFiles;
    this.state.autoRefreshActive = true;

    const hasWorkspace = !!vscode.workspace.workspaceFolders?.length;

    this.liveTimer = setInterval(async () => {
      const current = loadSettings();
      const hasWs = !!vscode.workspace.workspaceFolders?.length;
      if (hasWs && (current.liveScope === "workspace" || current.liveScope === "both")) {
        await this.scanWorkspace(false);
      }
      if (vscode.window.activeTextEditor && (current.liveScope === "file" || current.liveScope === "both")) {
        await this.scanCurrentFile(false);
      }
    }, settings.autoRefreshSeconds * 1000);

    this.pushState();
    if (hasWorkspace && (settings.liveScope === "workspace" || settings.liveScope === "both")) {
      this.scanWorkspace(false).then(() => {
        if (this.state.workspaceReport) {
          vscode.window.showInformationMessage(
            `EcoCode auto-scan complete: ${this.state.workspaceReport.total_files} files, ${this.state.workspaceReport.total_energy_wh} Wh`
          );
        }
      }).catch((error) => {
        this.log(`Live mode initial workspace scan failed: ${this.errorMessage(error)}`);
      });
    }
    if (vscode.window.activeTextEditor && (settings.liveScope === "file" || settings.liveScope === "both")) {
      this.scanCurrentFile(false).catch((error) => {
        this.log(`Live mode initial file scan failed: ${this.errorMessage(error)}`);
      });
    }

    if (showFeedback) {
      vscode.window.showInformationMessage(`EcoCode live mode started (${settings.autoRefreshSeconds}s).`);
    }
  }

  stopLiveMode(showFeedback = true): void {
    if (this.liveTimer) {
      clearInterval(this.liveTimer);
      this.liveTimer = undefined;
    }

    this.state.autoRefreshActive = false;
    this.pushState();

    if (showFeedback) {
      vscode.window.showInformationMessage("EcoCode live mode stopped.");
    }
  }

  //private startScanningUI(scope: "workspace" | "file"): void {
  //  this.state.isScanning = true;
  //  this.state.scanningScope = scope;
  //  // Animated dots in status bar: Scanning. → Scanning.. → Scanning...
  //  let dots = 1;
  //  const label = scope === "workspace" ? "workspace" : "file";
  //  const tick = (): void => {
  //    this.statusBar.text = `$(sync~spin) EcoCode: Scanning ${label}${".".repeat(dots)}`;
  //    dots = dots >= 3 ? 1 : dots + 1;
  //  };
  //  tick();
  //  this.statusBar.show();
  //  this.dotTimer = setInterval(tick, 500);
  //  this.pushState();
  //}

  //private endScanningUI(): void {
  //  if (this.dotTimer) {
  //    clearInterval(this.dotTimer);
  //    this.dotTimer = undefined;
  //  }
  //  this.state.isScanning = false;
  //  this.state.scanningScope = undefined;
  //  this.updateStatusBar();
  //}

  dispose(): void {
    //this.endScanningUI();
    this.stopLiveMode(false);
  }

  private getWorkspaceRoot(uri?: vscode.Uri): vscode.Uri | undefined {
    if (!vscode.workspace.workspaceFolders || vscode.workspace.workspaceFolders.length === 0) {
      return undefined;
    }
    if (!uri) {
      return vscode.workspace.workspaceFolders[0].uri;
    }
    return vscode.workspace.getWorkspaceFolder(uri)?.uri;
  }

  private pushState(): void {
    if (!this.view) {
      return;
    }
    this.view.webview.postMessage({
      type: "state",
      payload: this.state,
    });
  }

  private updateStatusBar(): void {
    if (this.state.workspaceReport) {
      this.statusBar.text = `$(pulse) EcoCode ${this.state.workspaceReport.total_energy_wh} Wh`;
      return;
    }
    this.statusBar.text = "$(pulse) EcoCode: idle";
  }

  private log(message: string): void {
    this.output.appendLine(`[${new Date().toISOString()}] ${message}`);
  }

  private checkSchemaVersion(version: number): void {
    if (
      !this.schemaWarningShown &&
      typeof version === "number" &&
      version > EcoCodeController.supportedSchemaVersion
    ) {
      this.schemaWarningShown = true;
      vscode.window.showWarningMessage(
        `EcoCode CLI reports schema version ${version}, newer than this extension supports (${EcoCodeController.supportedSchemaVersion}). Update the EcoCode extension to avoid display issues.`,
      );
    }
  }

  private async showScanError(scope: "workspace" | "file", message: string): Promise<void> {
    const label = scope === "workspace" ? "workspace" : "file";
    if (this.isCliMissingError(message)) {
      // Stop the live loop so it does not keep failing every interval until the CLI is installed.
      this.stopLiveMode(false);
      if (this.cliMissingPromptShown) {
        return;
      }
      this.cliMissingPromptShown = true;
      const action = await vscode.window.showWarningMessage(
        `EcoCode ${label} scan failed: CLI not found.`,
        "Setup CLI",
        "Open Settings",
        "Show Setup Guide",
      );
      if (action === "Setup CLI") {
        await this.setupCliInWorkspace();
      }
      if (action === "Open Settings") {
        await vscode.commands.executeCommand("workbench.action.openSettings", "ecocode.cliPath");
      }
      if (action === "Show Setup Guide") {
        await this.showSetupGuide();
      }
      return;
    }

    vscode.window.showErrorMessage(`EcoCode ${label} scan failed: ${message}`);
  }

  private isCliMissingError(message: string): boolean {
    const normalized = message.toLowerCase();
    return normalized.includes("ecocode cli not found") || normalized.includes("spawn ecocode enoent");
  }

  private errorMessage(error: unknown): string {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return String(error);
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const controller = new EcoCodeController(context);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("ecocode.insightsView", controller),
    vscode.commands.registerCommand("ecocode.openDashboard", async () => controller.focusDashboard()),
    vscode.commands.registerCommand("ecocode.scanWorkspace", async () => controller.scanWorkspace()),
    vscode.commands.registerCommand("ecocode.scanCurrentFile", async () => controller.scanCurrentFile()),
    vscode.commands.registerCommand("ecocode.configureScanFilters", async () => controller.configureScanFilters()),
    vscode.commands.registerCommand("ecocode.setupCliInWorkspace", async () => controller.setupCliInWorkspace()),
    vscode.commands.registerCommand("ecocode.showSetupGuide", async () => controller.showSetupGuide()),
    vscode.commands.registerCommand("ecocode.startAutoRefresh", () => controller.startLiveMode()),
    vscode.commands.registerCommand("ecocode.stopAutoRefresh", () => controller.stopLiveMode()),
    vscode.commands.registerCommand("ecocode.suggestForFile", async () => controller.suggestForFile()),
    vscode.commands.registerCommand(
      "ecocode.applyPatch",
      async (scriptPath: string, ruleId: string | undefined, useLlm: boolean) =>
        controller.applyPatch(scriptPath, ruleId, useLlm),
    ),
    { dispose: () => controller.dispose() },
  );
}

export function deactivate(): void {
  // Nothing to do, handled by disposables.
}
