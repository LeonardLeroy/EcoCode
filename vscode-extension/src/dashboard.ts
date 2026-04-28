import * as vscode from "vscode";

export function getDashboardHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
  const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "dashboard.css"));
  const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "dashboard.js"));
  const nonce = String(Date.now());

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EcoCode Insights</title>
  <link href="${styleUri}" rel="stylesheet" />
</head>
<body>
  <header class="topbar">
    <div>
      <h1>EcoCode Insights</h1>
      <p class="subtitle">Energy and runtime visibility for your workspace</p>
    </div>
    <div class="controls">
      <button id="refreshWorkspace">Scan Workspace</button>
      <button id="scanCurrentFile">Scan Current File</button>
      <span id="scanStatus" class="scan-status hidden"></span>
    </div>
  </header>

  <section class="filters">
    <label><input type="checkbox" id="showSummary" checked /> Summary</label>
    <label><input type="checkbox" id="showStability" checked /> Stability</label>
    <label><input type="checkbox" id="showFiles" checked /> Top Files</label>
    <label><input type="checkbox" id="showCurrentFile" checked /> Current File</label>
  </section>

  <section id="errorBox" class="card hidden"></section>

  <section id="summarySection" class="grid"></section>

  <section id="stabilitySection" class="card"></section>

  <section id="filesSection" class="card">
    <h2>Top Files by Estimated Energy</h2>
    <div id="filesTableWrapper"></div>
  </section>

  <section id="currentFileSection" class="card"></section>

  <footer class="footer">
    <span id="updatedAt">No data yet</span>
    <span id="autoRefreshState"></span>
  </footer>

  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}
