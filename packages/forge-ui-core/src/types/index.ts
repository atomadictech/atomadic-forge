/**
 * Canonical TypeScript contracts for every Atomadic Forge JSON output.
 * Mirrors the Python schemas in src/atomadic_forge/a0_qk_constants/.
 * Both forge-studio (Tauri) and forge-web (PWA) consume these.
 */

export type Tier = "a0" | "a1" | "a2" | "a3" | "a4";
export type TierOrUnknown = Tier | "unknown";

export interface TierDistribution {
  a0: number;
  a1: number;
  a2: number;
  a3: number;
  a4: number;
  unknown: number;
}

export interface EffectDistribution {
  pure: number;
  state: number;
  io: number;
}

export interface ScoutSymbol {
  name: string;
  kind: string;
  tier: TierOrUnknown;
  file: string;
  line: number;
  loc?: number;
  qualname?: string;
  effect?: "pure" | "state" | "io";
}

export interface ScoutReport {
  schema_version: string;
  project_root: string;
  python_file_count?: number;
  file_count?: number;
  symbol_count: number;
  tier_distribution: TierDistribution;
  effect_distribution?: EffectDistribution;
  symbols: ScoutSymbol[];
  recommendations?: string[];
  scanned_at?: string;
}

export type Verdict = "PASS" | "FAIL" | "REFINE" | "QUARANTINE" | "NEEDS_WORK";
export type ViolationSeverity = "error" | "warn" | "info";

export interface WireViolation {
  file: string;
  from_tier: string;
  to_tier: string;
  imported: string;
  language?: string;
  f_code: string;
  proposed_fix?: string;
  proposed_destination?: string;
  proposed_action?: "auto" | "review_manually";
  autofixable?: boolean;
  repair_suggestion?: string;
}

export interface WireReport {
  schema_version: string;
  source_dir: string;
  verdict?: Verdict;
  violations: WireViolation[];
  violation_count: number;
  auto_fixable?: number;
  autofixable_count?: number;
  files_scanned?: number;
}

export interface CertifyResult {
  schema_version: string;
  score: number;
  documentation_complete: boolean;
  tests_present: boolean;
  tier_layout_present: boolean;
  no_upward_imports: boolean;
  issues: string[];
}

export interface ReceiptSignatures {
  aaaa_nexus: null | { signature: string; key_id: string; signed_at: string };
  local_ed25519: null | { signature: string; public_key: string; signed_at: string };
}

export interface Receipt {
  schema_version: string;
  project: {
    name: string;
    root: string;
    package?: string;
    language?: string;
    languages?: Record<string, number>;
  };
  verdict: Verdict;
  forge_version: string;
  certify: CertifyResult;
  wire: { verdict: string; violation_count: number };
  scout: { symbol_count: number; tier_distribution: TierDistribution };
  signatures: ReceiptSignatures;
}

export type AgentPlanMode = "improve" | "absorb";
export type AgentActionKind =
  | "operational"
  | "architectural"
  | "composition"
  | "synthesis"
  | "release";
export type RiskLevel = "low" | "medium" | "high";

export interface AgentAction {
  id: string;
  kind: AgentActionKind;
  title: string;
  why: string;
  write_scope: number;
  risk: RiskLevel;
  applyable: boolean;
  next_command: string;
  related_fcodes?: string[];
}

export interface AgentPlan {
  schema_version: string;
  mode: AgentPlanMode;
  goal: string;
  verdict: Verdict;
  action_count: number;
  applyable_count: number;
  top_actions: AgentAction[];
  next_command: string;
  plan_id?: string;
  saved_at?: string;
}

export interface ContextPack {
  schema_version: string;
  repo_purpose: string;
  tier_law: string;
  blockers: string[];
  best_action: string;
  tests_status: string;
  certify_gate: string;
  risky_files: string[];
}

export interface PreflightResult {
  schema_version: string;
  detected_tier: TierOrUnknown;
  forbidden_imports: string[];
  likely_tests: string[];
  siblings: string[];
  write_scope: number;
  risk: RiskLevel;
  warnings: string[];
}

export interface DoctorResult {
  schema_version: string;
  python_version: string;
  forge_version: string;
  optional_deps: Record<string, { installed: boolean; version?: string }>;
  warnings: string[];
}

export interface RecipeChecklistItem {
  description: string;
  done: boolean;
  command?: string;
}

export interface Recipe {
  id: string;
  title: string;
  description: string;
  checklist: RecipeChecklistItem[];
  file_scope_hints: string[];
  validation_gate: string;
}

export interface SBOM {
  bomFormat: string;
  specVersion: string;
  serialNumber: string;
  version: number;
  components: Array<{
    type: string;
    name: string;
    version: string;
    purl?: string;
  }>;
}

export interface MctTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface McpResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

export interface DebtConfig {
  hourlyRate: number;
}

export interface ForgeConfig {
  provider: "ollama" | "gemini" | "anthropic" | "openai" | "auto";
  ollama_url?: string;
  ollama_model?: string;
  gemini_key?: string;
  anthropic_key?: string;
  openai_key?: string;
  default_target_score?: number;
  auto_apply?: boolean;
  output_dir?: string;
  sources_dir?: string;
  package_prefix?: string;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

// ─── Severity scoring ────────────────────────────────────────────────────
export const SEVERITY_WEIGHTS: Record<ViolationSeverity, number> = {
  error: 4,
  warn: 2,
  info: 1,
};

export function fCodeSeverity(fCode: string): number {
  if (fCode.startsWith("F004")) return 4;
  if (fCode.startsWith("F003")) return 2;
  return 1;
}

export function fCodeSeverityLabel(fCode: string): ViolationSeverity {
  const w = fCodeSeverity(fCode);
  if (w >= 4) return "error";
  if (w >= 2) return "warn";
  return "info";
}
