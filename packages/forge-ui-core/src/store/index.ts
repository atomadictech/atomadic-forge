/**
 * Shared zustand store. Identical state across both shells.
 */
import { create } from "zustand";
import type {
  AgentPlan,
  CertifyResult,
  ConnectionStatus,
  ContextPack,
  DebtConfig,
  ForgeConfig,
  McpResource,
  MctTool,
  Receipt,
  ScoutReport,
  Tier,
  WireReport,
} from "../types";

export interface ForgeState {
  // connection
  status: ConnectionStatus;
  projectRoot: string | null;
  error: string | null;

  // reports / artifacts
  scoutReport: ScoutReport | null;
  wireReport: WireReport | null;
  certifyResult: CertifyResult | null;
  contextPack: ContextPack | null;
  agentPlan: AgentPlan | null;
  receipt: Receipt | null;

  // mcp
  tools: MctTool[];
  resources: McpResource[];

  // ui
  selectedTier: Tier | null;
  debtConfig: DebtConfig;
  forgeConfig: ForgeConfig | null;

  // setters
  setStatus: (s: ConnectionStatus) => void;
  setProjectRoot: (p: string | null) => void;
  setError: (e: string | null) => void;
  setScoutReport: (r: ScoutReport | null) => void;
  setWireReport: (r: WireReport | null) => void;
  setCertifyResult: (r: CertifyResult | null) => void;
  setContextPack: (c: ContextPack | null) => void;
  setAgentPlan: (p: AgentPlan | null) => void;
  setReceipt: (r: Receipt | null) => void;
  setTools: (t: MctTool[]) => void;
  setResources: (r: McpResource[]) => void;
  setSelectedTier: (t: Tier | null) => void;
  setDebtConfig: (c: Partial<DebtConfig>) => void;
  setForgeConfig: (c: ForgeConfig | null) => void;
  reset: () => void;
}

export const useForgeStore = create<ForgeState>((set) => ({
  status: "disconnected",
  projectRoot: null,
  error: null,
  scoutReport: null,
  wireReport: null,
  certifyResult: null,
  contextPack: null,
  agentPlan: null,
  receipt: null,
  tools: [],
  resources: [],
  selectedTier: null,
  debtConfig: { hourlyRate: 80 },
  forgeConfig: null,

  setStatus: (s) => set({ status: s }),
  setProjectRoot: (p) => set({ projectRoot: p }),
  setError: (e) => set({ error: e }),
  setScoutReport: (r) => set({ scoutReport: r }),
  setWireReport: (r) => set({ wireReport: r }),
  setCertifyResult: (r) => set({ certifyResult: r }),
  setContextPack: (c) => set({ contextPack: c }),
  setAgentPlan: (p) => set({ agentPlan: p }),
  setReceipt: (r) => set({ receipt: r }),
  setTools: (t) => set({ tools: t }),
  setResources: (r) => set({ resources: r }),
  setSelectedTier: (t) => set({ selectedTier: t }),
  setDebtConfig: (c) => set((s) => ({ debtConfig: { ...s.debtConfig, ...c } })),
  setForgeConfig: (c) => set({ forgeConfig: c }),
  reset: () =>
    set({
      status: "disconnected",
      projectRoot: null,
      error: null,
      scoutReport: null,
      wireReport: null,
      certifyResult: null,
      contextPack: null,
      agentPlan: null,
      receipt: null,
      tools: [],
      resources: [],
      selectedTier: null,
    }),
}));
