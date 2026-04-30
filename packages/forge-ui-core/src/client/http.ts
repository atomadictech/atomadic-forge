/**
 * HttpForgeClient — implementation backed by an HTTP transport.
 *
 * Used by the Next.js PWA. The web shell exposes thin API routes under
 * /api/forge/<verb> that fork `forge mcp serve` server-side and proxy
 * MCP JSON-RPC. This class talks to those routes.
 *
 * If the verb has a dedicated route (e.g. /api/forge/recon), it's preferred.
 * Otherwise we fall through to /api/forge/call with { name, args }.
 */
import { ForgeClientError, type ForgeClient } from "./index";
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

export interface HttpForgeClientOptions {
  /** Base URL of the API. Default: "/api/forge" (same-origin Next.js routes). */
  baseUrl?: string;
  /** Fetch implementation. Default: globalThis.fetch. */
  fetch?: typeof fetch;
  /** Optional auth header. */
  authToken?: string;
}

export class HttpForgeClient implements ForgeClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;
  private readonly authToken?: string;

  constructor(opts: HttpForgeClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? "/api/forge").replace(/\/$/, "");
    this.fetcher = opts.fetch ?? globalThis.fetch.bind(globalThis);
    this.authToken = opts.authToken;
  }

  private async request<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (this.authToken) headers.authorization = `Bearer ${this.authToken}`;
    let res: Response;
    try {
      res = await this.fetcher(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      throw new ForgeClientError(`http:${path} failed: ${err}`, path, err);
    }
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new ForgeClientError(`http:${path} ${res.status}: ${text}`, path);
    }
    return (await res.json()) as T;
  }

  async connect(projectRoot: string): Promise<void> {
    await this.request<{ ok: boolean }>("/connect", { projectRoot });
  }
  async disconnect(): Promise<void> {
    await this.request<{ ok: boolean }>("/disconnect");
  }
  async toolsList(): Promise<MctTool[]> {
    const r = await this.request<{ tools: MctTool[] }>("/tools", undefined, "GET");
    return r.tools ?? [];
  }
  async resourcesList(): Promise<McpResource[]> {
    const r = await this.request<{ resources: McpResource[] }>("/resources", undefined, "GET");
    return r.resources ?? [];
  }
  callTool<T>(name: string, args: Record<string, unknown>): Promise<T> {
    return this.request<T>("/call", { name, args });
  }

  recon(target: string) {
    return this.request<ScoutReport>("/recon", { target });
  }
  cherry(args: { target: string; pick?: string[]; onlyTier?: string }) {
    return this.request<unknown>("/cherry", args);
  }
  finalize(args: { source: string; dest: string; opts?: Record<string, unknown> }) {
    return this.request<unknown>("/finalize", args);
  }
  auto(args: { source: string; dest: string; opts?: Record<string, unknown> }) {
    return this.request<unknown>("/auto", args);
  }
  wire(source: string, suggestRepairs = false) {
    return this.request<WireReport>("/wire", { source, suggest_repairs: suggestRepairs });
  }
  certify(source: string, opts: Record<string, unknown> = {}) {
    return this.request<CertifyResult>("/certify", { source, ...opts });
  }
  async status(source: string) {
    return this.request<{ wire: WireReport; certify: CertifyResult }>("/status", { source });
  }
  enforce(source: string, opts: { apply?: boolean } = {}) {
    return this.request<unknown>("/enforce", { source, apply: opts.apply ?? false });
  }
  plan(target: string, opts: Record<string, unknown> = {}) {
    return this.request<AgentPlan>("/plan", { target, ...opts });
  }
  planList() {
    return this.request<Array<{ id: string; goal: string; saved_at: string }>>(
      "/plan/list",
      undefined,
      "GET",
    );
  }
  planShow(id: string) {
    return this.request<AgentPlan>(`/plan/${encodeURIComponent(id)}`, undefined, "GET");
  }
  planStep(id: string, cardId: string, apply = false) {
    return this.request<unknown>(`/plan/${encodeURIComponent(id)}/step`, { cardId, apply });
  }
  planApply(id: string, apply = false) {
    return this.request<unknown>(`/plan/${encodeURIComponent(id)}/apply`, { apply });
  }
  contextPack(target: string) {
    return this.request<ContextPack>("/context-pack", { target });
  }
  preflight(reason: string, files: string[], scopeThreshold?: number) {
    return this.request<PreflightResult>("/preflight", { reason, files, scopeThreshold });
  }
  recipes() {
    return this.request<Recipe[]>("/recipes", undefined, "GET");
  }
  recipe(id: string) {
    return this.request<Recipe>(`/recipes/${encodeURIComponent(id)}`, undefined, "GET");
  }
  sbom(target: string, out?: string) {
    return this.request<unknown>("/sbom", { target, out });
  }
  iterate(opts: import("./index").IterateOptions) {
    return this.request<unknown>("/iterate", opts);
  }
  evolve(opts: import("./index").EvolveOptions) {
    return this.request<unknown>("/evolve", opts);
  }
  emergent(target: string) {
    return this.request<unknown>("/emergent", { target });
  }
  synergy(target: string) {
    return this.request<unknown>("/synergy", { target });
  }
  audit(target: string) {
    return this.request<unknown>("/audit", { target });
  }
  async receipt(target: string) {
    try {
      return await this.request<Receipt>("/receipt", { target });
    } catch {
      return null;
    }
  }
  cs1(receiptPath: string, out?: string) {
    return this.request<unknown>("/cs1", { receipt: receiptPath, out });
  }
  doctor() {
    return this.request<DoctorResult>("/doctor", undefined, "GET");
  }
  configShow() {
    return this.request<ForgeConfig>("/config", undefined, "GET");
  }
  async configSet(key: string, value: string) {
    await this.request<{ ok: boolean }>("/config", { key, value }, "PUT");
  }
  configTest() {
    return this.request<{ ok: boolean; message: string }>("/config/test", {});
  }

  async complexityScore(file: string) {
    const r = await this.request<{ score: number }>("/complexity", { file });
    return r.score;
  }
}
