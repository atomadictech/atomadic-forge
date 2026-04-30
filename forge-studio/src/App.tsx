import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useForgeStore } from "@/store";
import { Navigation, type AppTab } from "@/components/Navigation";
import { ErrorBanner } from "@/components/ErrorBanner";
import { ProjectScanDashboard } from "@/components/ProjectScanDashboard";
import { ArchitectureGraph } from "@/components/ArchitectureGraph";
import { ComplexityHeatmap } from "@/components/ComplexityHeatmap";
import { DebtCounter } from "@/components/DebtCounter";
import { AgentTopologyMap } from "@/components/AgentTopologyMap";

const queryClient = new QueryClient();

function StatusPip() {
  const { status, projectRoot } = useForgeStore();
  const colors: Record<string, string> = {
    connected: "bg-cyber-success",
    connecting: "bg-yellow-400 animate-pulse",
    error: "bg-cyber-alert",
    disconnected: "bg-cyber-border",
  };
  return (
    <div className="flex items-center gap-2 font-mono text-[10px] text-monolith-muted">
      <span className={`w-1.5 h-1.5 rounded-full ${colors[status] ?? colors.disconnected}`} />
      {projectRoot
        ? <span className="hidden sm:inline truncate max-w-[260px]">{projectRoot}</span>
        : <span>disconnected</span>}
    </div>
  );
}

export function App() {
  const [activeTab, setActiveTab] = useState<AppTab>("scan");
  const [navOpen, setNavOpen] = useState(true);

  const sidebarW = navOpen ? "lg:pl-56" : "lg:pl-14";

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex flex-col h-screen overflow-hidden bg-cyber-dark text-cyber-chrome">
        <Navigation active={activeTab} onSelect={setActiveTab} open={navOpen} setOpen={setNavOpen} />

        {/* Top bar */}
        <header className={`h-12 border-b border-cyber-border bg-cyber-panel flex items-center px-4 gap-4 flex-shrink-0 transition-all duration-300 ${sidebarW}`}>
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyber-cyan lg:hidden">⬡ Forge Studio</span>
          <div className="flex-1" />
          <StatusPip />
        </header>

        {/* Error banner */}
        <div className={`transition-all duration-300 ${sidebarW}`}>
          <ErrorBanner />
        </div>

        {/* Main content */}
        <main className={`flex-1 overflow-y-auto transition-all duration-300 ${sidebarW} pb-16 lg:pb-0`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="h-full"
            >
              {activeTab === "scan"     && <ProjectScanDashboard />}
              {activeTab === "graph"    && <ArchitectureGraph />}
              {activeTab === "heatmap"  && <ComplexityHeatmap />}
              {activeTab === "debt"     && <DebtCounter />}
              {activeTab === "topology" && <AgentTopologyMap />}
              {activeTab === "settings" && <SettingsPanel />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </QueryClientProvider>
  );
}

function SettingsPanel() {
  const { debtConfig, setDebtConfig } = useForgeStore();
  return (
    <div className="p-8 max-w-lg">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.3em] text-monolith-muted mb-8">Configuration</h2>
      <div className="border border-cyber-border bg-cyber-panel p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-cyber-chrome">Hourly Rate</div>
            <div className="text-[9px] text-monolith-muted mt-1">Used by the CISQ debt counter</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-monolith-muted font-mono text-xs">$</span>
            <input
              type="number" min={1} max={999} value={debtConfig.hourlyRate}
              onChange={(e) => setDebtConfig({ hourlyRate: Number(e.target.value) || 80 })}
              className="w-20 bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-sm px-2 py-1 focus:outline-none focus:border-cyber-cyan"
            />
            <span className="text-monolith-muted font-mono text-xs">/hr</span>
          </div>
        </div>
        <div className="border-t border-cyber-border pt-4 text-[9px] text-monolith-muted font-mono space-y-1">
          <div>F004x structural violations · weight 4</div>
          <div>F003x effect violations · weight 2</div>
          <div>other F-codes · weight 1</div>
        </div>
      </div>
    </div>
  );
}
