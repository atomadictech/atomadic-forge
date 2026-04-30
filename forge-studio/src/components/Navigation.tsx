import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { Layers, BarChart3, Flame, TrendingDown, Network, Settings, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type AppTab = "scan" | "graph" | "heatmap" | "debt" | "topology" | "settings";

interface NavItem { id: AppTab; label: string; icon: React.ElementType; description: string; }

const NAV: NavItem[] = [
  { id: "scan",     label: "Scan",         icon: Layers,       description: "Scout + Wire + Certify" },
  { id: "graph",    label: "Architecture", icon: BarChart3,    description: "5-Tier Monadic Graph" },
  { id: "heatmap",  label: "Complexity",   icon: Flame,        description: "Cognitive Heatmap" },
  { id: "debt",     label: "Debt",         icon: TrendingDown, description: "CISQ Debt Counter" },
  { id: "topology", label: "Topology",     icon: Network,      description: "MCP Tool Graph" },
  { id: "settings", label: "Settings",     icon: Settings,     description: "Configuration" },
];

export function Navigation({
  active, onSelect, open, setOpen,
}: {
  active: AppTab;
  onSelect: (t: AppTab) => void;
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 bottom-0 z-50 bg-cyber-panel border-r border-cyber-border transition-all duration-300 hidden lg:flex flex-col",
        open ? "w-56" : "w-14",
      )}>
        <div className="h-12 px-3 border-b border-cyber-border flex items-center justify-between overflow-hidden">
          <AnimatePresence mode="wait">
            {open && (
              <motion.span
                key="label"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-cyan whitespace-nowrap"
              >
                ⬡ FORGE STUDIO
              </motion.span>
            )}
          </AnimatePresence>
          <button
            onClick={() => setOpen(!open)}
            className="p-1 text-monolith-muted hover:text-cyber-cyan transition-colors flex-shrink-0"
          >
            {open ? <X size={14} /> : <Menu size={14} />}
          </button>
        </div>

        <nav className="flex-1 py-4 flex flex-col gap-0.5">
          {NAV.map((item) => {
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelect(item.id)}
                className={cn(
                  "group relative flex items-center gap-3 px-3 py-2.5 transition-all text-left w-full",
                  isActive ? "text-cyber-cyan bg-cyber-cyan/5" : "text-monolith-muted hover:text-cyber-chrome",
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-active-bar"
                    className="absolute left-0 top-0 bottom-0 w-[2px] bg-cyber-cyan"
                  />
                )}
                <item.icon size={16} className="flex-shrink-0" />
                <AnimatePresence mode="wait">
                  {open && (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      transition={{ duration: 0.15 }}
                      className="flex flex-col overflow-hidden"
                    >
                      <span className="text-[10px] font-mono uppercase tracking-widest leading-none">{item.label}</span>
                      <span className="text-[8px] text-monolith-muted mt-0.5 whitespace-nowrap">{item.description}</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </button>
            );
          })}
        </nav>

        {/* Footer version */}
        <div className="px-3 py-3 border-t border-cyber-border overflow-hidden">
          <AnimatePresence mode="wait">
            {open && (
              <motion.span
                key="ver"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.4 }}
                exit={{ opacity: 0 }}
                className="font-mono text-[8px] text-monolith-muted"
              >
                atomadic-forge 0.3.2
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-cyber-panel/95 backdrop-blur-sm border-t border-cyber-border">
        <nav className="flex justify-around px-2 py-1">
          {NAV.map((item) => {
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelect(item.id)}
                className={cn(
                  "relative flex flex-col items-center gap-0.5 px-2 py-1.5 transition-all",
                  isActive ? "text-cyber-cyan" : "text-monolith-muted",
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="mobile-nav-active"
                    className="absolute -top-px left-1 right-1 h-[2px] bg-cyber-cyan"
                  />
                )}
                <item.icon size={16} />
                <span className="text-[7px] font-mono uppercase tracking-tight">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </>
  );
}
