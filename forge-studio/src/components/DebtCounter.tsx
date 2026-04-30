import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useForgeStore } from "@/store";
import * as mcp from "@/lib/mcp";
import { fCodeSeverity } from "@/lib/types";
import { ActionableCard } from "@/components/ui/ActionableCard";
import type { WireReport } from "@/lib/types";

function computeDebt(r: WireReport, rate: number): number {
  return r.violations.reduce((t, v) => t + fCodeSeverity(v.f_code) * rate, 0);
}

function fmtUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export function DebtCounter() {
  const { projectRoot, wireReport, debtConfig, setWireReport, setDebtConfig } = useForgeStore();
  const [prevDebt, setPrevDebt] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const iRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const debt = wireReport ? computeDebt(wireReport, debtConfig.hourlyRate) : null;

  useEffect(() => {
    if (debt === null || prevDebt === null) { setPrevDebt(debt); return; }
    if (debt < prevDebt) setFlash("down");
    else if (debt > prevDebt) setFlash("up");
    setPrevDebt(debt);
    const t = setTimeout(() => setFlash(null), 800);
    return () => clearTimeout(t);
  }, [debt]);

  useEffect(() => {
    if (!projectRoot) return;
    iRef.current = setInterval(async () => {
      try { const r = await mcp.callWire(projectRoot, true); setWireReport(r); } catch { }
    }, 5000);
    return () => { if (iRef.current) clearInterval(iRef.current); };
  }, [projectRoot]);

  if (!wireReport) {
    return (
      <div className="p-6 max-w-4xl">
        <ActionableCard title="Technical Debt" delay={0}>
          <div className="h-40 flex items-center justify-center border border-dashed border-cyber-border">
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
              Scan a project to compute debt
            </span>
          </div>
        </ActionableCard>
      </div>
    );
  }

  const debtColor = flash === "down" ? "text-cyber-success" : flash === "up" ? "text-cyber-alert" : "text-cyber-chrome";
  const f004 = wireReport.violations.filter((v) => v.f_code?.startsWith("F004")).length;
  const f003 = wireReport.violations.filter((v) => v.f_code?.startsWith("F003")).length;
  const other = wireReport.violations.filter((v) => !v.f_code?.startsWith("F004") && !v.f_code?.startsWith("F003")).length;

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <ActionableCard title="Technical Debt" delay={0}>
        <div className="flex flex-col items-center py-4 gap-4">
          <div
            data-testid="debt-counter"
            className={`font-mono font-bold tabular-nums tracking-tight transition-colors duration-300 ${debtColor}`}
            style={{ fontSize: "clamp(2.5rem, 6vw, 4rem)" }}
          >
            {debt !== null ? fmtUsd(debt) : "—"}
          </div>
          <div className="font-mono text-[9px] uppercase tracking-widest text-monolith-muted">
            estimated tech debt principal
          </div>
          <AnimatePresence>
            {flash === "down" && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="font-mono text-[10px] text-cyber-success"
              >
                ▼ debt reduced
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="border-t border-cyber-border pt-4 grid grid-cols-3 gap-2">
          {([
            ["F004x · structural", f004, "text-cyber-alert", "border-cyber-alert/20"],
            ["F003x · effect", f003, "text-amber-400", "border-amber-400/20"],
            ["other", other, "text-blue-400", "border-blue-400/20"],
          ] as [string, number, string, string][]).map(([label, cnt, color, border]) => (
            <div key={label} className={`bg-cyber-dark border ${border} px-3 py-2 text-center`}>
              <div className={`font-mono font-bold text-lg ${color}`}>{cnt}</div>
              <div className="font-mono text-[8px] uppercase tracking-widest text-monolith-muted mt-0.5">{label}</div>
            </div>
          ))}
        </div>

        <div className="border-t border-cyber-border pt-4 flex items-center gap-3">
          <label htmlFor="hr" className="font-mono text-[9px] uppercase tracking-widest text-monolith-muted flex-1">
            Hourly rate (USD)
          </label>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-monolith-muted">$</span>
            <input
              id="hr"
              type="number"
              min={1}
              max={500}
              value={debtConfig.hourlyRate}
              onChange={(e) => setDebtConfig({ hourlyRate: Number(e.target.value) || 80 })}
              className="w-20 bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-sm px-2 py-1 focus:outline-none focus:border-cyber-cyan"
            />
            <span className="font-mono text-xs text-monolith-muted">/hr</span>
          </div>
        </div>

        <div className="border-t border-cyber-border pt-3 font-mono text-[8px] text-monolith-muted space-y-0.5">
          <div>CISQ formula: violations × weight × hourly_rate · polls every 5 s</div>
          <div>F004x weight 4 · F003x weight 2 · other weight 1</div>
        </div>
      </ActionableCard>
    </div>
  );
}
