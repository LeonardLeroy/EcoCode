import * as vscode from "vscode";
import { getDashboardHtml } from "./dashboard";
import { loadSettings, profileScript, profileWorkspace } from "./ecocodeRunner";
import { DashboardState } from "./types";

class EcoCodeController implements vscode.WebviewViewProvider {
  private view: vscode.WebviewView | undefined;
  private readonly output = vscode.window.createOutputChannel("EcoCode Insights");
  private readonly statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  private liveTimer: NodeJS.Timeout | undefined;
  private workspaceScanInFlight = false;
  private fileScanInFlight = false;

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

    this.context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor(() => {
        const settings = loadSettings();
        if (!settings.liveModeEnabled) {
          return;
        }
        if (settings.liveScope === "file" || settings.liveScope === "both") {
          void this.scanCurrentFile(false);
        }
      }),
      vscode.workspace.onDidSaveTextDocument((document) => {
        const settings = loadSettings();
        if (!settings.liveModeEnabled) {
          return;
        }
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor || activeEditor.document.uri.toString() !== document.uri.toString()) {
          return;
        }
        if (settings.liveScope === "file" || settings.liveScope === "both") {
          void this.scanCurrentFile(false);
        }
      }),
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
    if (initialSettings.liveModeEnabled) {
      this.startLiveMode(false);
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
    try {
      const report = await profileWorkspace(workspaceRoot.fsPath);
      this.state.workspaceReport = report;
      this.state.updatedAtIso = new Date().toISOString();
      this.state.lastError = undefined;
      this.log("Workspace scan complete.");
      this.updateStatusBar();
      this.pushState();
      if (showFeedback) {
        vscode.window.showInformationMessage(`EcoCode scan complete: ${report.total_files} files, ${report.total_energy_wh} Wh`);
      }
    } catch (error) {
      const message = this.errorMessage(error);
      this.state.lastError = message;
      this.state.updatedAtIso = new Date().toISOString();
      this.log(`Workspace scan failed: ${message}`);
      this.pushState();
      vscode.window.showErrorMessage(`EcoCode workspace scan failed: ${message}`);
    } finally {
      this.workspaceScanInFlight = false;
    }
  }

  async scanCurrentFile(showFeedback = true): Promise<void> {
    if (this.fileScanInFlight) {
      return;
    }

    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      if (showFeedback) {
        vscode.window.showWarningMessage("Open a file before running current file scan.");
      }
      return;
    }

    const workspaceRoot = this.getWorkspaceRoot(editor.document.uri);
    if (!workspaceRoot) {
      vscode.window.showWarningMessage("Current file is not inside an open workspace folder.");
      return;
    }

    this.fileScanInFlight = true;
    try {
      const report = await profileScript(editor.document.uri.fsPath, workspaceRoot.fsPath);
      this.state.scriptReport = report;
      this.state.updatedAtIso = new Date().toISOString();
      this.state.lastError = undefined;
      this.log(`Current file scan complete: ${report.script}`);
      this.pushState();
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
      this.pushState();
      vscode.window.showErrorMessage(`EcoCode file scan failed: ${message}`);
    } finally {
      this.fileScanInFlight = false;
    }
  }

  async configureScanFilters(): Promise<void> {
    const config = vscode.workspace.getConfiguration("ecocode");
    const currentCollector = config.get<string>("collector", "placeholder");
    const currentMaxFiles = config.get<number>("maxFiles", 200);
    const currentRuns = config.get<number>("runs", 1);
    const currentExt = (config.get<string[]>("extensions", []) || []).join(", ");
    const currentInclude = (config.get<string[]>("includeGlobs", []) || []).join(", ");
    const currentExclude = (config.get<string[]>("excludeGlobs", []) || []).join(", ");

    const collector = await vscode.window.showQuickPick(["placeholder", "runtime"], {
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

    this.liveTimer = setInterval(async () => {
      const current = loadSettings();
      if (current.liveScope === "workspace" || current.liveScope === "both") {
        await this.scanWorkspace(false);
      }
      if (current.liveScope === "file" || current.liveScope === "both") {
        await this.scanCurrentFile(false);
      }
    }, settings.autoRefreshSeconds * 1000);

    this.pushState();
    if (settings.liveScope === "workspace" || settings.liveScope === "both") {
      this.scanWorkspace(false).catch((error) => {
        this.log(`Live mode initial workspace scan failed: ${this.errorMessage(error)}`);
      });
    }
    if (settings.liveScope === "file" || settings.liveScope === "both") {
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

  dispose(): void {
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
    vscode.commands.registerCommand("ecocode.startAutoRefresh", () => controller.startLiveMode()),
    vscode.commands.registerCommand("ecocode.stopAutoRefresh", () => controller.stopLiveMode()),
    { dispose: () => controller.dispose() },
  );
}

export function deactivate(): void {
  // Nothing to do, handled by disposables.
}
