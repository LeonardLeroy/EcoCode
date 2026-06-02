import * as path from "node:path";
import * as vscode from "vscode";
import { getOptimizationSuggestions, loadSettings } from "./ecocodeRunner";
import { EcoCodeSuggestReport, EcoCodeSuggestion } from "./types";

export const ECOCODE_DIAGNOSTIC_SOURCE = "EcoCode";

// Rules the CLI can turn into an automatic patch (see optimizer._select_patch_suggestion).
const PATCHABLE_RULE_IDS = new Set(["PY001", "PY002"]);

const SUPPORTED_EXTENSIONS = new Set([
  ".py",
  ".js",
  ".mjs",
  ".cjs",
  ".ts",
  ".jsx",
  ".tsx",
  ".c",
  ".cpp",
  ".cc",
  ".cxx",
  ".h",
  ".hpp",
  ".cs",
  ".rs",
  ".html",
  ".htm",
  ".css",
  ".s",
  ".asm",
]);

export function isSupportedDocument(document: vscode.TextDocument): boolean {
  if (document.uri.scheme !== "file") {
    return false;
  }
  return SUPPORTED_EXTENSIONS.has(path.extname(document.fileName).toLowerCase());
}

function isPythonDocument(document: vscode.TextDocument): boolean {
  return path.extname(document.fileName).toLowerCase() === ".py";
}

function severityForImpact(impact: string): vscode.DiagnosticSeverity {
  if (impact === "high") {
    return vscode.DiagnosticSeverity.Warning;
  }
  if (impact === "medium") {
    return vscode.DiagnosticSeverity.Information;
  }
  return vscode.DiagnosticSeverity.Hint;
}

function toDiagnostic(document: vscode.TextDocument, suggestion: EcoCodeSuggestion): vscode.Diagnostic {
  const lastLine = Math.max(0, document.lineCount - 1);
  const lineIndex =
    suggestion.line && suggestion.line > 0 ? Math.min(suggestion.line - 1, lastLine) : 0;
  const range = document.lineAt(lineIndex).range;

  const diagnostic = new vscode.Diagnostic(
    range,
    `${suggestion.title} — ${suggestion.rationale}`,
    severityForImpact(suggestion.impact),
  );
  diagnostic.source = ECOCODE_DIAGNOSTIC_SOURCE;
  diagnostic.code = suggestion.rule_id;
  return diagnostic;
}

/**
 * Runs `ecocode optimize suggest` for supported documents and publishes the
 * results as native diagnostics (squiggles). Refreshes are debounced so typing
 * does not spawn a CLI process on every keystroke.
 */
export class EcoCodeSuggestionManager {
  private readonly collection = vscode.languages.createDiagnosticCollection("ecocode");
  private readonly timers = new Map<string, NodeJS.Timeout>();
  private readonly reports = new Map<string, EcoCodeSuggestReport>();

  constructor(
    private readonly resolveWorkspace: (uri: vscode.Uri) => string | undefined,
    private readonly log: (message: string) => void,
    private readonly onReport: (uri: vscode.Uri, report: EcoCodeSuggestReport) => void,
  ) {}

  scheduleRefresh(document: vscode.TextDocument, delayMs = 600): void {
    if (!isSupportedDocument(document) || !loadSettings().diagnosticsEnabled) {
      return;
    }
    const key = document.uri.toString();
    const existing = this.timers.get(key);
    if (existing) {
      clearTimeout(existing);
    }
    this.timers.set(
      key,
      setTimeout(() => {
        this.timers.delete(key);
        void this.refresh(document);
      }, delayMs),
    );
  }

  async refresh(
    document: vscode.TextDocument,
    includeLlm = false,
  ): Promise<EcoCodeSuggestReport | undefined> {
    if (!isSupportedDocument(document)) {
      return undefined;
    }
    const workspaceRoot = this.resolveWorkspace(document.uri);
    if (!workspaceRoot) {
      return undefined;
    }

    try {
      const report = await getOptimizationSuggestions(document.uri.fsPath, workspaceRoot, includeLlm);
      this.reports.set(document.uri.toString(), report);
      this.collection.set(
        document.uri,
        report.suggestions.map((suggestion) => toDiagnostic(document, suggestion)),
      );
      this.onReport(document.uri, report);
      return report;
    } catch (error) {
      // Best-effort: a missing CLI is surfaced by the main scan flow, not here.
      this.log(`Suggestion refresh failed for ${document.fileName}: ${(error as Error).message}`);
      return undefined;
    }
  }

  getReport(uri: vscode.Uri): EcoCodeSuggestReport | undefined {
    return this.reports.get(uri.toString());
  }

  clear(uri: vscode.Uri): void {
    this.collection.delete(uri);
    this.reports.delete(uri.toString());
  }

  dispose(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
    this.collection.dispose();
  }
}

/**
 * Offers quick-fixes for EcoCode diagnostics. Patch generation is Python-only in
 * the CLI, so actions are only provided for `.py` files.
 */
export class EcoCodeCodeActionProvider implements vscode.CodeActionProvider {
  static readonly providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  provideCodeActions(
    document: vscode.TextDocument,
    _range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
  ): vscode.CodeAction[] {
    if (!isPythonDocument(document)) {
      return [];
    }

    const actions: vscode.CodeAction[] = [];
    for (const diagnostic of context.diagnostics) {
      if (diagnostic.source !== ECOCODE_DIAGNOSTIC_SOURCE) {
        continue;
      }
      const ruleId = typeof diagnostic.code === "string" ? diagnostic.code : String(diagnostic.code ?? "");
      if (!PATCHABLE_RULE_IDS.has(ruleId)) {
        continue;
      }

      const action = new vscode.CodeAction(
        `EcoCode: apply automatic fix (${ruleId})`,
        vscode.CodeActionKind.QuickFix,
      );
      action.diagnostics = [diagnostic];
      action.command = {
        command: "ecocode.applyPatch",
        title: "Apply EcoCode fix",
        arguments: [document.uri.fsPath, ruleId, false],
      };
      actions.push(action);
    }

    const llmAction = new vscode.CodeAction(
      "EcoCode: generate optimized candidate (LLM)",
      vscode.CodeActionKind.QuickFix,
    );
    llmAction.command = {
      command: "ecocode.applyPatch",
      title: "Generate optimized candidate (LLM)",
      arguments: [document.uri.fsPath, undefined, true],
    };
    actions.push(llmAction);

    return actions;
  }
}
