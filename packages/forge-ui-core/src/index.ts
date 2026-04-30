// ─── Theme ──────────────────────────────────────────────────────────────
// Consumers import "@atomadic/forge-ui-core/theme.css" directly.

// ─── Types ──────────────────────────────────────────────────────────────
export * from "./types";

// ─── Store ──────────────────────────────────────────────────────────────
export { useForgeStore, type ForgeState } from "./store";

// ─── Client abstraction ─────────────────────────────────────────────────
export type {
  ForgeClient,
  CertifyOptions,
  AutoOptions,
  PlanOptions,
  EnforceOptions,
  IterateOptions,
  EvolveOptions,
} from "./client";
export { ForgeClientError } from "./client";
export { ForgeClientProvider, useForgeClient } from "./client/context";
export { TauriForgeClient, type TauriForgeClientOptions } from "./client/tauri";
export { HttpForgeClient, type HttpForgeClientOptions } from "./client/http";
export { StubForgeClient } from "./client/stub";

// ─── Utilities ──────────────────────────────────────────────────────────
export { cn } from "./utils/cn";

// ─── Components ─────────────────────────────────────────────────────────
export { ActionableCard } from "./components/ui/ActionableCard";
export { NeonButton } from "./components/ui/NeonButton";
export { PipelineStepper, type PipelineStep } from "./components/ui/PipelineStepper";
export { ScoreGauge } from "./components/ui/ScoreGauge";

export { Navigation, type AppTab } from "./components/Navigation";
export { ErrorBanner } from "./components/ErrorBanner";
export { StatusPip } from "./components/StatusPip";
export { ProjectScanDashboard } from "./components/ProjectScanDashboard";
export { ArchitectureGraph } from "./components/ArchitectureGraph";
export { ComplexityHeatmap } from "./components/ComplexityHeatmap";
export { DebtCounter } from "./components/DebtCounter";
export { AgentTopologyMap } from "./components/AgentTopologyMap";
export { CertifyDashboard } from "./components/CertifyDashboard";
export { AgentPlanDashboard } from "./components/AgentPlanDashboard";
export { DoctorPanel } from "./components/DoctorPanel";
export { SettingsPanel } from "./components/SettingsPanel";

// ─── Shell ──────────────────────────────────────────────────────────────
export { ForgeShell, type ForgeShellProps } from "./shell/ForgeShell";
