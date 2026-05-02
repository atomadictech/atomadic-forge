/**
 * StubForgeClient — deterministic fake for development, Storybook, and tests.
 * No process spawning, no network. Returns realistic shapes from the real
 * forge JSON contracts.
 */
import type { ForgeClient } from "./index";
import { ForgeClientError } from "./index";
import type {
  AgentPlan,
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

const SAMPLE_SCOUT: ScoutReport = {
  schema_version: "atomadic-forge.scout/v1",
  project_root: "<stub>",
  python_file_count: 53,
  file_count: 53,
  symbol_count: 222,
  tier_distribution: { a0: 18, a1: 64, a2: 41, a3: 73, a4: 24, unknown: 2 },
  effect_distribution: { pure: 142, state: 58, io: 22 },
  symbols: [
    { name: "TierDistribution", kind: "class", tier: "a0", file: "src/types.py", line: 12, loc: 6 },
    { name: "classify_tier", kind: "function", tier: "a1", file: "src/utils.py", line: 88, loc: 24 },
    { name: "ManifestStore", kind: "class", tier: "a2", file: "src/store.py", line: 14, loc: 110 },
    { name: "ForgePipeline", kind: "class", tier: "a3", file: "src/pipeline.py", line: 7, loc: 187 },
    { name: "main", kind: "function", tier: "a4", file: "src/cli.py", line: 1, loc: 42 },
  ],
  recommendations: [
    "Strong tier distribution; review 2 unknown-tier symbols",
    "a3 (features) is dominant — healthy composition layer",
  ],
  scanned_at: new Date().toISOString(),
};

const SAMPLE_WIRE: WireReport = {
  schema_version: "atomadic-forge.wire/v1",
  source_dir: "<stub>",
  verdict: "PASS",
  violations: [],
  violation_count: 0,
  auto_fixable: 0,
  files_scanned: 53,
};

const SAMPLE_CERTIFY: CertifyResult = {
  schema_version: "atomadic-forge.certify/v1",
  score: 92,
  documentation_complete: true,
  tests_present: true,
  tier_layout_present: true,
  no_upward_imports: true,
  issues: [],
};

const SAMPLE_CONTEXT_PACK: ContextPack = {
  schema_version: "atomadic-forge.context_pack/v1",
  repo_purpose: "Atomadic Forge — absorb arbitrary code into 5-tier monadic architecture.",
  tier_law: "a0→a1→a2→a3→a4. Never import upward. Compose, don't rewrite.",
  blockers: [],
  best_action: "All gates green — ship.",
  tests_status: "841 passing",
  certify_gate: "92/100 (≥75 required)",
  risky_files: [],
};

const SAMPLE_PLAN: AgentPlan = {
  schema_version: "atomadic-forge.agent_plan/v1",
  mode: "improve",
  goal: "Maintain release readiness",
  verdict: "PASS",
  action_count: 0,
  applyable_count: 0,
  top_actions: [],
  next_command: "forge status",
};

const SAMPLE_DOCTOR: DoctorResult = {
  schema_version: "atomadic-forge.doctor/v1",
  python_version: "3.12.4",
  forge_version: "0.3.2",
  optional_deps: {
    complexipy: { installed: true, version: "1.0.0" },
    cryptography: { installed: true, version: "43.0.0" },
    tomli: { installed: true, version: "2.0.1" },
  },
  warnings: [],
};

const SAMPLE_CONFIG: ForgeConfig = {
  provider: "auto",
  default_target_score: 75,
  auto_apply: false,
};

export class StubForgeClient implements ForgeClient {
  private connected = false;

  async connect(_root: string): Promise<void> {
    this.connected = true;
  }
  async disconnect(): Promise<void> {
    this.connected = false;
  }
  private requireConnected(verb: string): void {
    if (!this.connected)
      throw new ForgeClientError(`StubForgeClient: not connected (${verb})`, verb);
  }

  async toolsList(): Promise<MctTool[]> {
    return [
      { name: "recon", description: "Scout symbols", inputSchema: {} },
      { name: "wire", description: "Validate tier imports", inputSchema: {} },
      { name: "certify", description: "Score conformance", inputSchema: {} },
    ];
  }
  async resourcesList(): Promise<McpResource[]> {
    return [
      {
        uri: "forge://docs/receipt",
        name: "Receipt schema",
        mimeType: "text/markdown",
      },
    ];
  }
  async callTool<T>(name: string, _args: Record<string, unknown>): Promise<T> {
    throw new ForgeClientError(`stub callTool(${name}) not implemented`, "callTool");
  }

  async recon(_target: string): Promise<ScoutReport> {
    this.requireConnected("recon");
    return SAMPLE_SCOUT;
  }
  async cherry() {
    return { ok: true };
  }
  async finalize() {
    return { ok: true };
  }
  async auto() {
    return { ok: true };
  }
  async wire(_source: string): Promise<WireReport> {
    this.requireConnected("wire");
    return SAMPLE_WIRE;
  }
  async certify(_source: string): Promise<CertifyResult> {
    this.requireConnected("certify");
    return SAMPLE_CERTIFY;
  }
  async status(source: string) {
    return { wire: await this.wire(source), certify: await this.certify(source) };
  }
  async enforce() {
    return { ok: true };
  }
  async plan(): Promise<AgentPlan> {
    return SAMPLE_PLAN;
  }
  async planList() {
    return [];
  }
  async planShow(_id: string): Promise<AgentPlan> {
    return SAMPLE_PLAN;
  }
  async planStep() {
    return { ok: true };
  }
  async planApply() {
    return { ok: true };
  }
  async contextPack(_target: string): Promise<ContextPack> {
    return SAMPLE_CONTEXT_PACK;
  }
  async preflight(): Promise<PreflightResult> {
    return {
      schema_version: "atomadic-forge.preflight/v1",
      detected_tier: "a3",
      forbidden_imports: [],
      likely_tests: [],
      siblings: [],
      write_scope: 0,
      risk: "low",
      warnings: [],
    };
  }
  async recipes(): Promise<Recipe[]> {
    return [];
  }
  async recipe(id: string): Promise<Recipe> {
    return {
      id,
      title: id,
      description: "stub",
      checklist: [],
      file_scope_hints: [],
      validation_gate: "forge status",
    };
  }
  async sbom() {
    return { ok: true };
  }
  async iterate() {
    return { ok: true };
  }
  async evolve() {
    return { ok: true };
  }
  async emergent() {
    return { ok: true };
  }
  async synergy() {
    return { ok: true };
  }
  async audit() {
    return { ok: true };
  }
  async receipt(_target: string): Promise<Receipt | null> {
    return null;
  }
  async cs1() {
    return { ok: true };
  }
  async doctor(): Promise<DoctorResult> {
    return SAMPLE_DOCTOR;
  }
  async configShow(): Promise<ForgeConfig> {
    return SAMPLE_CONFIG;
  }
  async configSet(_k: string, _v: string): Promise<void> {}
  async configTest() {
    return { ok: true, message: "stub" };
  }
}
