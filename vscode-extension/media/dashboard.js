const vscode = acquireVsCodeApi();

const byId = (id) => document.getElementById(id);

const el = {
  refreshWorkspace: byId("refreshWorkspace"),
  scanCurrentFile: byId("scanCurrentFile"),
  showSummary: byId("showSummary"),
  showStability: byId("showStability"),
  showFiles: byId("showFiles"),
  showCurrentFile: byId("showCurrentFile"),
  errorBox: byId("errorBox"),
  summarySection: byId("summarySection"),
  stabilitySection: byId("stabilitySection"),
  filesSection: byId("filesSection"),
  filesTableWrapper: byId("filesTableWrapper"),
  currentFileSection: byId("currentFileSection"),
  updatedAt: byId("updatedAt"),
  autoRefreshState: byId("autoRefreshState"),
  scanStatus: byId("scanStatus"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderMetrics(report) {
  if (!report) {
    el.summarySection.innerHTML = "<div class='metric'><h3>Status</h3><strong>No workspace scan yet</strong></div>";
    return;
  }

  el.summarySection.innerHTML = `
    <article class="metric"><h3>Total files</h3><strong>${report.total_files}</strong></article>
    <article class="metric"><h3>Total CPU (s)</h3><strong>${report.total_cpu_seconds}</strong></article>
    <article class="metric"><h3>Total memory (MB)</h3><strong>${report.total_memory_mb}</strong></article>
    <article class="metric"><h3>Total estimated Wh</h3><strong>${report.total_energy_wh}</strong></article>
    <article class="metric"><h3>Average sustainability</h3><strong>${report.average_sustainability_score}/100</strong></article>
    <article class="metric"><h3>Collector</h3><strong>${report.collector}</strong></article>
  `;
}

function renderStability(report) {
  if (!report || !report.stability) {
    el.stabilitySection.innerHTML = "<h2>Stability</h2><p>No repeated-run stability data yet.</p>";
    return;
  }

  const unstable = report.stability.unstable;
  const cls = unstable ? "error" : "";
  const status = unstable ? "UNSTABLE" : "Stable";
  function formatCvValue(v) {
    if (v === null || v === undefined) return "n/a";
    if (typeof v === "number") return Number(v).toFixed(3);
    return String(v);
  }

  const cv = report.summary ? formatCvValue(report.summary.total_energy_wh_cv_pct) : "n/a";
  el.stabilitySection.innerHTML = `
    <h2>Stability</h2>
    <p class="${cls}">Status: <strong>${status}</strong></p>
    <p>Energy variability (CV %): <strong>${cv}</strong></p>
    <p>Threshold (%): <strong>${report.stability.max_energy_cv_pct}</strong></p>
  `;
}

function renderFiles(report, topLimit) {
  if (!report || !Array.isArray(report.files) || report.files.length === 0) {
    el.filesTableWrapper.innerHTML = "<p>No file-level data yet.</p>";
    return;
  }

  const sorted = [...report.files].sort((a, b) => b.estimated_energy_wh - a.estimated_energy_wh);
  const rows = sorted
    .slice(0, topLimit)
    .map((f) => {
      const safePath = escapeHtml(f.script);
      return `<tr>
        <td class="file-cell" title="${safePath}"><span class="file-path">${safePath}</span></td>
        <td>${f.cpu_seconds}</td>
        <td>${f.memory_mb}</td>
        <td>${f.estimated_energy_wh}</td>
        <td>${f.sustainability_score}</td>
      </tr>`;
    })
    .join("");

  el.filesTableWrapper.innerHTML = `
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>File</th>
            <th>CPU (s)</th>
            <th>Memory (MB)</th>
            <th>Energy (Wh)</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderCurrentFile(report) {
  if (!report) {
    el.currentFileSection.innerHTML = "<h2>Current File</h2><p>No current file scan yet.</p>";
    return;
  }

  function formatCvValue(v) {
    if (v === null || v === undefined) return "n/a (single run)";
    if (typeof v === "number") return Number(v).toFixed(3);
    return String(v);
  }

  const safePath = escapeHtml(report.script);
  const runs = report.runs || 1;
  const cv = report.summary ? formatCvValue(report.summary.estimated_energy_wh_cv_pct) : formatCvValue(undefined);
  el.currentFileSection.innerHTML = `
    <h2>Current File</h2>
    <p class="current-file-path"><strong class="file-path">${safePath}</strong></p>
    <p>CPU: ${report.cpu_seconds}s | Memory: ${report.memory_mb}MB | Energy: ${report.estimated_energy_wh}Wh</p>
    <p>Sustainability score: <strong>${report.sustainability_score}/100</strong> | Energy variability (CV %): <strong>${cv}</strong> <small>(runs: ${runs})</small></p>
  `;
}

function applyVisibility() {
  el.summarySection.classList.toggle("hidden", !el.showSummary.checked);
  el.stabilitySection.classList.toggle("hidden", !el.showStability.checked);
  el.filesSection.classList.toggle("hidden", !el.showFiles.checked);
  el.currentFileSection.classList.toggle("hidden", !el.showCurrentFile.checked);
}

function render(state) {
  // Loading state
  const scanning = !!state.isScanning;
  el.refreshWorkspace.disabled = scanning;
  el.scanCurrentFile.disabled = scanning;

  if (scanning) {
    const label = state.scanningScope === "file" ? "file" : "workspace";
    el.scanStatus.textContent = `Scanning ${label}…`;
    el.scanStatus.classList.remove("hidden");
  } else {
    el.scanStatus.classList.add("hidden");
    el.scanStatus.textContent = "";
  }

  el.errorBox.classList.toggle("hidden", !state.lastError);
  el.errorBox.classList.toggle("error", !!state.lastError);
  el.errorBox.textContent = state.lastError || "";

  renderMetrics(state.workspaceReport);
  renderStability(state.workspaceReport);
  const topLimit = Number.isFinite(state.showTopFiles) ? state.showTopFiles : 15;
  renderFiles(state.workspaceReport, topLimit);
  renderCurrentFile(state.scriptReport);

  el.updatedAt.textContent = `Last update: ${new Date(state.updatedAtIso).toLocaleString()}`;
  el.autoRefreshState.textContent = state.autoRefreshActive
    ? `Live mode every ${state.autoRefreshSeconds}s`
    : "Live mode stopped";

  applyVisibility();
}

el.refreshWorkspace.addEventListener("click", () => {
  vscode.postMessage({ type: "scanWorkspace" });
});

el.scanCurrentFile.addEventListener("click", () => {
  vscode.postMessage({ type: "scanCurrentFile" });
});

for (const checkbox of [el.showSummary, el.showStability, el.showFiles, el.showCurrentFile]) {
  checkbox.addEventListener("change", applyVisibility);
}

window.addEventListener("message", (event) => {
  const message = event.data;
  if (message.type === "state") {
    render(message.payload);
  }
});

vscode.postMessage({ type: "ready" });
