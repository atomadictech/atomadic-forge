import { useEffect, useRef, useState } from "react";
import { useForgeStore } from "@/store";
import * as mcp from "@/lib/mcp";
import { SEVERITY_WEIGHTS } from "@/lib/types";
import type { WireReport } from "@/lib/types";
function computeDebt(r: WireReport, rate: number): number {
  return r.violations.reduce((t, v) => t + (SEVERITY_WEIGHTS[v.severity] ?? 1) * rate, 0);
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
    if (debt < prevDebt) setFlash("down"); else if (debt > prevDebt) setFlash("up");
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
  if (!wireReport) return null;
  const fc = flash === "down" ? "#4ade80" : flash === "up" ? "#f87171" : "#f1f5f9";
  return (
    <section style={{ padding: 24 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "#f1f5f9" }}>Technical Debt Counter</h2>
      <p style={{ fontSize: 12, color: "#64748b", marginBottom: 16 }}>CISQ: error=4, warn=2, info=1 × hourly_rate. Polls every 5 s.</p>
      <div data-testid="debt-counter" style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: "24px 32px", display: "inline-flex", flexDirection: "column", alignItems: "center", minWidth: 220, marginBottom: 20 }}>
        <div style={{ fontSize: 48, fontWeight: 800, color: fc, transition: "color 0.3s ease", letterSpacing: "-1px" }}>
          {debt !== null ? fmtUsd(debt) : "—"}
        </div>
        <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>estimated tech debt principal</div>
        {flash === "down" && <div style={{ color: "#4ade80", fontSize: 12, marginTop: 4 }}>▼ debt reduced</div>}
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16, fontSize: 13 }}>
        {(["error", "warn", "info"] as const).map((sev) => {
          const cnt = wireReport.violations.filter((v) => v.severity === sev).length;
          const c = { error: "#f87171", warn: "#fbbf24", info: "#60a5fa" };
          return (<div key={sev} style={{ background: "#0f172a", border: `1px solid ${c[sev]}33`, borderRadius: 6, padding: "6px 14px", display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ color: c[sev], fontWeight: 700 }}>{cnt}</span>
            <span style={{ color: "#64748b" }}>{sev}</span>
          </div>);
        })}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
        <label style={{ color: "#94a3b8" }} htmlFor="hr">Hourly rate (USD)</label>
        <input id="hr" type="number" min={1} max={500} value={debtConfig.hourlyRate}
          onChange={(e) => setDebtConfig({ hourlyRate: Number(e.target.value) || 80 })}
          style={{ width: 80, background: "#0f172a", border: "1px solid #334155", borderRadius: 4, padding: "4px 8px", color: "#e2e8f0", fontSize: 13 }} />
      </div>
    </section>
  );
}