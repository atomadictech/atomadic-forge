/**
 * ForgeClient — backend abstraction layer.
 * Tauri shell injects a Tauri-IPC implementation; web shell injects an HTTP one.
 * This is the *only* surface UI components touch — they never know the transport.
 */
import type {
  AgentPlan,
  AgentPlanMode,
  CertifyResult,
  ContextPack,
  DoctorResult,
  ForgeConfig,
  McpResource,
  MctTool,
  PreflightResult,
  Receipt,
  Recipe,
  ScoutReport,
  WireReport,
} from "../types";

// ─── Option types ────────────────────────────────────────────────────────
export interface CertifyOptions {
  failUnder?: number;
  emitReceipt?: boolean;
  receiptPath?: string;
  sign?: boolean;
  localSign?: boolean;
}

export interface AutoOptions {
  apply?: boolean;
  packageName?: string;
  onConflict?: "rename" | "first" | "last" | "fail";
  seedDeterminism?: number;
}

export interface PlanOptions {
  goal?: string;
  mode?: AgentPlanMode;
  top?: number;
  save?: boolean;
}

export interface EnforceOptions {
  apply?: boolean;
}

export interface IterateOptions {
  intent: string;
  outdir: string;
  provider?: ForgeConfig["provider"];
  apply?: boolean;
}

export interface EvolveOptions extends IterateOptions {
  rounds?: number;
  targetScore?: number;
}

// ─── The contract ────────────────────────────────────────────────────────
export interface ForgeClient {
  // Connection lifecycle
  connect(projectRoot: string): Promise<void>;
  disconnect(): Promise<void>;

  // MCP introspection
  toolsList(): Promise<MctTool[]>;
  resourcesList(): Promise<McpResource[]>;
  callTool<T = unknown>(name: string, args: Record<string, unknown>): Promise<T>;

  // Core absorption pipeline
  recon(target: string): Promise<ScoutReport>;
  cherry(args: { target: string; pick?: string[]; onlyTier?: string }): Promise<unknown>;
  finalize(args: { source: string; dest: string; opts?: AutoOptions }): Promise<unknown>;
  auto(args: { source: string; dest: string; opts?: AutoOptions }): Promise<unknown>;

  // Wiring & validation
  wire(source: string, suggestRepairs?: boolean): Promise<WireReport>;
  certify(source: string, opts?: CertifyOptions): Promise<CertifyResult>;
  status(source: string): Promise<{ wire: WireReport; certify: CertifyResult }>;
  enforce(source: string, opts?: EnforceOptions): Promise<unknown>;

  // Agent planning
  plan(target: string, opts?: PlanOptions): Promise<AgentPlan>;
  planList(): Promise<Array<{ id: string; goal: string; saved_at: string }>>;
  planShow(id: string): Promise<AgentPlan>;
  planStep(id: string, cardId: string, apply?: boolean): Promise<unknown>;
  planApply(id: string, apply?: boolean): Promise<unknown>;

  // Agent copilot
  contextPack(target: string): Promise<ContextPack>;
  preflight(reason: string, files: string[], scopeThreshold?: number): Promise<PreflightResult>;

  // Recipes & SBOM
  recipes(): Promise<Recipe[]>;
  recipe(id: string): Promise<Recipe>;
  sbom(target: string, out?: string): Promise<unknown>;

  // LLM loops
  iterate(opts: IterateOptions): Promise<unknown>;
  evolve(opts: EvolveOptions): Promise<unknown>;

  // Specialty verbs
  emergent(target: string): Promise<unknown>;
  synergy(target: string): Promise<unknown>;
  audit(target: string): Promise<unknown>;

  // Receipts & conformance
  receipt(target: string): Promise<Receipt | null>;
  cs1(receiptPath: string, out?: string): Promise<unknown>;

  // Diagnostics
  doctor(): Promise<DoctorResult>;
  /** Cognitive complexity score for a single file (0–100). Optional capability. */
  complexityScore?(file: string): Promise<number>;

  // Config
  configShow(): Promise<ForgeConfig>;
  configSet(key: string, value: string): Promise<void>;
  configTest(): Promise<{ ok: boolean; message: string }>;
}

export class ForgeClientError extends Error {
  constructor(
    message: string,
    public readonly verb: string,
    public readonly cause?: unknown,
  ) {
    super(message);
    this.name = "ForgeClientError";
  }
}
