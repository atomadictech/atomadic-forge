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

// ─── Scout report normalizer ─────────────────────────────────────────────────
// The CLI emits long-form tier keys (a0_qk_constants) and long-form symbol
// tier_guess / lineno fields. Normalize everything to the canonical short form.
const TIER_LONG: Record<string, Tier> = {
  a0_qk_constants: "a0",
  a1_at_functions: "a1",
  a2_mo_composites: "a2",
  a3_og_features: "a3",
  a4_sy_orchestration: "a4",
};

function shortTier(t: unknown): TierOrUnknown {
  if (typeof t !== "string") return "unknown";
  return TIER_LONG[t] ?? (/^a[0-4]$/.test(t) ? (t as Tier) : "unknown");
}

export function normalizeDoctorResult(raw: Record<string, unknown>): DoctorResult {
  const rawDeps = (raw.optional_deps ?? {}) as Record<string, unknown>;
  const optional_deps: Record<string, { installed: boolean; version?: string }> = {};
  for (const [name, val] of Object.entries(rawDeps)) {
    if (typeof val === "object" && val !== null && "installed" in val) {
      optional_deps[name] = val as { installed: boolean; version?: string };
    } else {
      const s = String(val);
      optional_deps[name] = s === "missing" ? { installed: false } : { installed: true, version: s === "ok" ? undefined : s };
    }
  }
  return {
    schema_version: String(raw.schema_version ?? ""),
    forge_version: String(raw.forge_version ?? raw.atomadic_forge_version ?? ""),
    python_version: String(raw.python_version ?? raw.python ?? ""),
    optional_deps,
    warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
  };
}

export function normalizeScoutReport(raw: Record<string, unknown>): ScoutReport {
  const rawDist = (raw.tier_distribution ?? {}) as Record<string, number>;
  const dist: TierDistribution = { a0: 0, a1: 0, a2: 0, a3: 0, a4: 0, unknown: 0 };
  for (const [k, v] of Object.entries(rawDist)) {
    const s = shortTier(k);
    dist[s] = (dist[s] ?? 0) + (v ?? 0);
  }
  const rawSyms = (raw.symbols ?? []) as Record<string, unknown>[];
  const symbols: ScoutSymbol[] = rawSyms.map((s) => ({
    name: String(s.name ?? ""),
    kind: String(s.kind ?? ""),
    tier: shortTier(s.tier_guess ?? s.tier),
    file: String(s.file ?? ""),
    line: Number(s.lineno ?? s.line ?? 0),
    qualname: s.qualname as string | undefined,
    effect: (Array.isArray(s.effects) ? s.effects[0] : s.effect) as ScoutSymbol["effect"],
  }));
  return {
    ...(raw as unknown as ScoutReport),
    project_root: String(raw.project_root ?? raw.repo ?? ""),
    tier_distribution: dist,
    symbols,
  };
}

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
