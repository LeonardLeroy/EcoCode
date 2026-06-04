export type CollectorType = "placeholder" | "runtime" | "static";

export interface EcoCodeRepoFileResult {
  script: string;
  cpu_seconds: number;
  memory_mb: number;
  estimated_energy_wh: number;
  sustainability_score: number;
  measured?: boolean;
  method?: string;
}

export interface EcoCodeSuggestion {
  rule_id: string;
  title: string;
  rationale: string;
  impact: "low" | "medium" | "high";
  confidence: number;
  language: string;
  line?: number | null;
}

export interface EcoCodeSuggestReport {
  schemaVersion: number;
  command: string;
  script: string;
  suggestion_count: number;
  suggestions: EcoCodeSuggestion[];
}

export interface EcoCodePatchReport {
  schemaVersion: number;
  command: string;
  script: string;
  candidate_path: string;
  rule_id: string;
  strategy_title: string;
  applied: boolean;
  changes_count: number;
  diff: string;
}

export interface EcoCodeRepoReport {
  schemaVersion: number;
  root: string;
  collector: CollectorType;
  runs: number;
  total_files: number;
  total_discovered?: number;
  total_cpu_seconds: number;
  total_memory_mb: number;
  total_energy_wh: number;
  average_sustainability_score: number;
  summary?: {
    runs: number;
    total_energy_wh_mean: number;
    total_energy_wh_median: number;
    total_energy_wh_stddev: number;
    total_energy_wh_cv_pct: number;
  };
  stability?: {
    max_energy_cv_pct: number;
    unstable: boolean;
  };
  extensions?: string[];
  include_globs?: string[];
  exclude_globs?: string[];
  files: EcoCodeRepoFileResult[];
}

export interface EcoCodeScriptReport {
  schemaVersion: number;
  script: string;
  collector: CollectorType;
  runs: number;
  cpu_seconds: number;
  memory_mb: number;
  estimated_energy_wh: number;
  sustainability_score: number;
  measured?: boolean;
  method?: string;
  summary?: {
    cpu_seconds_mean: number;
    cpu_seconds_median: number;
    cpu_seconds_stddev: number;
    memory_mb_mean: number;
    memory_mb_median: number;
    memory_mb_stddev: number;
    estimated_energy_wh_mean: number;
    estimated_energy_wh_median: number;
    estimated_energy_wh_stddev: number;
    estimated_energy_wh_cv_pct: number;
    sustainability_score_mean: number;
    sustainability_score_min: number;
    sustainability_score_max: number;
  };
}

export interface DashboardState {
  updatedAtIso: string;
  autoRefreshActive: boolean;
  autoRefreshSeconds: number;
  showTopFiles: number;
  //isScanning?: boolean;
  //scanningScope?: "workspace" | "file";
  workspaceReport?: EcoCodeRepoReport;
  scriptReport?: EcoCodeScriptReport;
  scriptSuggestions?: EcoCodeSuggestReport;
  lastError?: string;
}
