/**
 * TauriForgeClient — implementation backed by the Tauri Rust bridge that
 * spawns `forge mcp serve` and proxies MCP JSON-RPC over stdin/stdout.
 *
 * The Tauri side exposes these commands (see forge-studio/src-tauri/src/lib.rs):
 *   forge_connect, forge_disconnect, forge_tools_list, forge_resources_list, forge_call_tool
 *
 * Every higher-level verb routes through forge_call_tool with the canonical
 * MCP tool name. This way we don't need to change the Rust side as we add verbs.
 */
import { ForgeClientError, type ForgeClient } from "./index";
import { normalizeDoctorResult, normalizeScoutReport } from "../types";
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

// We type `invoke` as a generic so consumers can pass the @tauri-apps/api invoke
// without forcing this package to take a hard dep on it.
type Invoke = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;

export interface TauriForgeClientOptions {
  invoke: Invoke;
}

export class TauriForgeClient implements ForgeClient {
  constructor(private readonly opts: TauriForgeClientOptions) {}

  private async cmd<T>(name: string, args?: Record<string, unknown>): Promise<T> {
    try {
      return await this.opts.invoke<T>(name, args);
    } catch (err) {
      throw new ForgeClientError(`tauri:${name} failed: ${err}`, name, err);
    }
  }

  async connect(projectRoot: string): Promise<void> {
    await this.cmd<string>("forge_connect", { projectRoot });
  }
  async disconnect(): Promise<void> {
    await this.cmd<void>("forge_disconnect");
  }
  async toolsList(): Promise<MctTool[]> {
    const r = await this.cmd<{ tools: MctTool[] }>("forge_tools_list");
    return r.tools ?? [];
  }
  async resourcesList(): Promise<McpResource[]> {
    const r = await this.cmd<{ resources: McpResource[] }>("forge_resources_list");
    return r.resources ?? [];
  }
  async callTool<T>(name: string, args: Record<string, unknown>): Promise<T> {
    return this.cmd<T>("forge_call_tool", { name, arguments: args });
  }

  async recon(target: string): Promise<ScoutReport> {
    const raw = await this.callTool<Record<string, unknown>>("recon", { target });
    return normalizeScoutReport(raw);
  }
  cherry(args: { target: string; pick?: string[]; onlyTier?: string }) {
    return this.callTool("cherry", { ...args, only_tier: args.onlyTier });
  }
  finalize(args: { source: string; dest: string; opts?: Record<string, unknown> }) {
    return this.callTool("finalize", { source: args.source, dest: args.dest, ...(args.opts ?? {}) });
  }
  auto(args: { source: string; dest: string; opts?: Record<string, unknown> }) {
    return this.callTool("auto", { source: args.source, dest: args.dest, ...(args.opts ?? {}) });
  }
  wire(source: string, suggestRepairs = false) {
    return this.callTool<WireReport>("wire", { source, suggest_repairs: suggestRepairs });
  }
  certify(source: string, opts: Record<string, unknown> = {}) {
    return this.callTool<CertifyResult>("certify", { source, ...opts });
  }
  async status(source: string) {
    const [wire, certify] = await Promise.all([this.wire(source, false), this.certify(source)]);
    return { wire, certify };
  }
  enforce(source: string, opts: { apply?: boolean } = {}) {
    return this.callTool("enforce", { source, apply: opts.apply ?? false });
  }
  plan(target: string, opts: Record<string, unknown> = {}) {
    return this.callTool<AgentPlan>("auto_plan", { target, ...opts });
  }
  planList() {
    return this.callTool<Array<{ id: string; goal: string; saved_at: string }>>("plan_list", {});
  }
  planShow(id: string) {
    return this.callTool<AgentPlan>("plan_show", { id });
  }
  planStep(id: string, cardId: string, apply = false) {
    return this.callTool("auto_step", { id, card_id: cardId, apply });
  }
  planApply(id: string, apply = false) {
    return this.callTool("auto_apply", { id, apply });
  }
  contextPack(target: string) {
    return this.callTool<ContextPack>("context_pack", { target });
  }
  preflight(reason: string, files: string[], scopeThreshold?: number) {
    return this.callTool<PreflightResult>("preflight_change", {
      reason,
      files,
      scope_threshold: scopeThreshold,
    });
  }
  recipes() {
    return this.callTool<Recipe[]>("list_recipes", {});
  }
  recipe(id: string) {
    return this.callTool<Recipe>("get_recipe", { id });
  }
  sbom(target: string, out?: string) {
    return this.callTool("sbom", { target, out });
  }
  iterate(opts: import("./index").IterateOptions) {
    return this.callTool("iterate", { ...opts });
  }
  evolve(opts: import("./index").EvolveOptions) {
    return this.callTool("evolve", { ...opts });
  }
  emergent(target: string) {
    return this.callTool("emergent", { target });
  }
  synergy(target: string) {
    return this.callTool("synergy", { target });
  }
  audit(target: string) {
    return this.callTool("audit_list", { target });
  }
  async receipt(target: string): Promise<Receipt | null> {
    try {
      return await this.callTool<Receipt>("receipt", { target });
    } catch {
      return null;
    }
  }
  cs1(receiptPath: string, out?: string) {
    return this.callTool("cs1", { receipt: receiptPath, out });
  }
  async doctor(): Promise<DoctorResult> {
    const raw = await this.callTool<Record<string, unknown>>("doctor", {});
    return normalizeDoctorResult(raw);
  }
  configShow() {
    return this.callTool<ForgeConfig>("config_show", {});
  }
  async configSet(key: string, value: string) {
    await this.callTool("config_set", { key, value });
  }
  configTest() {
    return this.callTool<{ ok: boolean; message: string }>("config_test", {});
  }

  /** Tauri-specific: forwards to the Rust-side complexipy_score command. */
  complexityScore(file: string) {
    return this.cmd<number>("complexipy_score", { file });
  }
}
