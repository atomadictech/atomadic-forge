/**
 * ForgeShell — the canonical Atomadic Forge UI.
 *
 * Both shells render this. The only difference between Tauri and Web is the
 * `client` prop and the optional `brand`/`version` strings.
 *
 *   <ForgeShell client={tauriClient} brand="FORGE STUDIO" />
 *   <ForgeShell client={webClient}   brand="FORGE WEB"    />
 *
 * The UI is byte-identical otherwise.
 */
import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ForgeClientProvider } from "../client/context";
import type { ForgeClient } from "../client";
import { Navigation, type AppTab } from "../components/Navigation";
import { ErrorBanner } from "../components/ErrorBanner";
import { StatusPip } from "../components/StatusPip";
import { ProjectScanDashboard } from "../components/ProjectScanDashboard";
import { ArchitectureGraph } from "../components/ArchitectureGraph";
import { ComplexityHeatmap } from "../components/ComplexityHeatmap";
import { DebtCounter } from "../components/DebtCounter";
import { AgentTopologyMap } from "../components/AgentTopologyMap";
import { CertifyDashboard } from "../components/CertifyDashboard";
import { AgentPlanDashboard } from "../components/AgentPlanDashboard";
import { DoctorPanel } from "../components/DoctorPanel";
import { SettingsPanel } from "../components/SettingsPanel";

export interface ForgeShellProps {
  client: ForgeClient;
  /** Sidebar brand label, default "FORGE STUDIO". */
  brand?: string;
  /** Footer version string, default "atomadic-forge 0.3.4". */
  version?: string;
  /** Optional extra content to render at the right of the top bar (e.g. install-PWA button). */
  topBarRight?: ReactNode;
}

export function ForgeShell({
  client,
  brand = "FORGE STUDIO",
  version = "atomadic-forge 0.3.4",
  topBarRight,
}: ForgeShellProps) {
  const [activeTab, setActiveTab] = useState<AppTab>("scan");
  const [navOpen, setNavOpen] = useState(true);

  const sidebarW = navOpen ? "lg:pl-56" : "lg:pl-14";

  return (
    <ForgeClientProvider client={client}>
      <div className="flex flex-col h-screen overflow-hidden bg-cyber-dark text-cyber-chrome">
        <Navigation
          active={activeTab}
          onSelect={setActiveTab}
          open={navOpen}
          setOpen={setNavOpen}
          brand={brand}
          version={version}
        />

        <header
          className={`h-12 border-b border-cyber-border bg-cyber-panel flex items-center px-4 gap-4 flex-shrink-0 transition-all duration-300 ${sidebarW}`}
        >
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyber-cyan lg:hidden">
            ⬡ {brand}
          </span>
          <div className="flex-1" />
          {topBarRight}
          <StatusPip />
        </header>

        <div className={`transition-all duration-300 ${sidebarW}`}>
          <ErrorBanner />
        </div>

        <main
          className={`flex-1 overflow-y-auto transition-all duration-300 ${sidebarW} pb-16 lg:pb-0`}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="h-full"
            >
              {activeTab === "scan" && <ProjectScanDashboard />}
              {activeTab === "graph" && <ArchitectureGraph />}
              {activeTab === "heatmap" && <ComplexityHeatmap />}
              {activeTab === "debt" && <DebtCounter />}
              {activeTab === "certify" && <CertifyDashboard />}
              {activeTab === "plan" && <AgentPlanDashboard />}
              {activeTab === "topology" && <AgentTopologyMap />}
              {activeTab === "doctor" && <DoctorPanel />}
              {activeTab === "settings" && <SettingsPanel />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </ForgeClientProvider>
  );
}
