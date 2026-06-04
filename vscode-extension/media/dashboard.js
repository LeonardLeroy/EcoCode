const vscode = acquireVsCodeApi();

const byId = (id) => document.getElementById(id);

const el = {
  refreshWorkspace: byId("refreshWorkspace"),
  scanCurrentFile: byId("scanCurrentFile"),
  showSummary: byId("showSummary"),
  showStability: byId("showStability"),
  showFiles: byId("showFiles"),
  showCurrentFile: byId("showCurrentFile"),
  showSuggestions: byId("showSuggestions"),
  errorBox: byId("errorBox"),
  truncationBanner: byId("truncationBanner"),
  summarySection: byId("summarySection"),
  stabilitySection: byId("stabilitySection"),
  filesSection: byId("filesSection"),
  filesTableWrapper: byId("filesTableWrapper"),
  currentFileSection: byId("currentFileSection"),
  suggestionsSection: byId("suggestionsSection"),
  suggestionsWrapper: byId("suggestionsWrapper"),
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

function methodLabel(entry) {
  if (!entry) return "";
  if (entry.measured === true) return "measured";
  if (entry.method === "static_estimate") return "estimated";
  if (entry.method === "placeholder") return "synthetic";
  return entry.method || "";
}

function methodBadge(entry) {
  const label = methodLabel(entry);
  if (!label) return "";
  return ` <span class="badge badge-${label}">${label}</span>`;
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

function renderTruncation(report) {
  const discovered = report && report.total_discovered;
  if (!report || typeof discovered !== "number" || discovered <= report.total_files) {
    el.truncationBanner.classList.add("hidden");
    el.truncationBanner.innerHTML = "";
    return;
  }
  el.truncationBanner.classList.remove("hidden");
  el.truncationBanner.innerHTML =
    `<strong>Partial scan:</strong> showing <strong>${report.total_files}</strong> of <strong>${discovered}</strong> matching files (file limit reached). ` +
    `Totals below cover the scanned subset only. ` +
    `<button id="increaseLimitBtn">Increase limit</button>`;
  const button = byId("increaseLimitBtn");
  if (button) {
    button.addEventListener("click", () => vscode.postMessage({ type: "increaseMaxFiles" }));
  }
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
        <td class="file-cell" title="${safePath}"><span class="file-path">${safePath}</span>${methodBadge(f)}</td>
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
    <p class="current-file-path"><strong class="file-path">${safePath}</strong>${methodBadge(report)}</p>
    <p>CPU: ${report.cpu_seconds}s | Memory: ${report.memory_mb}MB | Energy: ${report.estimated_energy_wh}Wh</p>
    <p>Sustainability score: <strong>${report.sustainability_score}/100</strong> | Energy variability (CV %): <strong>${cv}</strong> <small>(runs: ${runs})</small></p>
  `;
}

function impactRank(impact) {
  if (impact === "high") return 0;
  if (impact === "medium") return 1;
  return 2;
}

function renderSuggestions(report) {
  if (!report || !Array.isArray(report.suggestions) || report.suggestions.length === 0) {
    el.suggestionsWrapper.innerHTML = "<p>No optimization suggestions for the current file.</p>";
    return;
  }

  const sorted = [...report.suggestions].sort((a, b) => impactRank(a.impact) - impactRank(b.impact));
  const items = sorted
    .map((s) => {
      const location = s.line ? ` <small>(line ${s.line})</small>` : "";
      const confidence = typeof s.confidence === "number" ? s.confidence.toFixed(2) : s.confidence;
      return `<li>
        <span class="badge badge-impact-${escapeHtml(s.impact)}">${escapeHtml(s.impact)}</span>
        <strong>[${escapeHtml(s.rule_id)}]</strong> ${escapeHtml(s.title)}${location}
        <div class="suggestion-why">${escapeHtml(s.rationale)} <small>confidence ${confidence}</small></div>
      </li>`;
    })
    .join("");

  el.suggestionsWrapper.innerHTML = `<ul class="suggestion-list">${items}</ul>`;
}

function applyVisibility() {
  el.summarySection.classList.toggle("hidden", !el.showSummary.checked);
  el.stabilitySection.classList.toggle("hidden", !el.showStability.checked);
  el.filesSection.classList.toggle("hidden", !el.showFiles.checked);
  el.currentFileSection.classList.toggle("hidden", !el.showCurrentFile.checked);
  el.suggestionsSection.classList.toggle("hidden", !el.showSuggestions.checked);
}

function render(state) {
  // Loading state
  /*const scanning = !!state.isScanning;
  el.refreshWorkspace.disabled = scanning;
  el.scanCurrentFile.disabled = scanning;

  if (scanning) {
    const label = state.scanningScope === "file" ? "file" : "workspace";
    el.scanStatus.textContent = `Scanning ${label}…`;
    el.scanStatus.classList.remove("hidden");
  } else {
    el.scanStatus.classList.add("hidden");
    el.scanStatus.textContent = "";
  }*/
  el.refreshWorkspace.disabled = false;
  el.scanCurrentFile.disabled = false;

  el.errorBox.classList.toggle("hidden", !state.lastError);
  el.errorBox.classList.toggle("error", !!state.lastError);
  el.errorBox.textContent = state.lastError || "";

  renderTruncation(state.workspaceReport);
  renderMetrics(state.workspaceReport);
  renderStability(state.workspaceReport);
  const topLimit = Number.isFinite(state.showTopFiles) ? state.showTopFiles : 15;
  renderFiles(state.workspaceReport, topLimit);
  renderCurrentFile(state.scriptReport);
  renderSuggestions(state.scriptSuggestions);

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

for (const checkbox of [el.showSummary, el.showStability, el.showFiles, el.showCurrentFile, el.showSuggestions]) {
  checkbox.addEventListener("change", applyVisibility);
}

window.addEventListener("message", (event) => {
  const message = event.data;
  if (message.type === "state") {
    render(message.payload);
  }
});

vscode.postMessage({ type: "ready" });
