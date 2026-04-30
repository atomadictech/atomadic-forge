import { useState } from "react";
import { motion } from "motion/react";
import { FolderSearch, Zap, AlertTriangle, Wrench } from "lucide-react";
import { useForgeStore } from "../store";
import { useForgeClient } from "../client/context";
import { ActionableCard } from "./ui/ActionableCard";
import { NeonButton } from "./ui/NeonButton";
import type { Tier } from "../types";

const TC: Record<Tier | "unknown", string> = {
  a0: "#818cf8",
  a1: "#34d399",
  a2: "#60a5fa",
  a3: "#f472b6",
  a4: "#fb923c",
  unknown: "#6b7280",
};
const TL: Record<Tier | "unknown", string> = {
  a0: "a0 · Constants",
  a1: "a1 · Functions",
  a2: "a2 · Composites",
  a3: "a3 · Features",
  a4: "a4 · Orchestration",
  unknown: "Unknown",
};

export function ProjectScanDashboard() {
  const {
    status,
    projectRoot,
    scoutReport,
    wireReport,
    selectedTier,
    setProjectRoot,
    setStatus,
    setError,
    setScoutReport,
    setWireReport,
    setTools,
    setResources,
    setSelectedTier,
  } = useForgeStore();
  const client = useForgeClient();
  const [inputPath, setInputPath] = useState(projectRoot ?? "");
  const [scanning, setScanning] = useState(false);

  async function handleScan() {
    const root = inputPath.trim();
    if (!root) return;
    setScanning(true);
    setError(null);
    try {
      setStatus("connecting");
      await client.connect(root);
      setProjectRoot(root);
      setStatus("connected");
      const [tools, resources, scout, wire] = await Promise.all([
        client.toolsList(),
        client.resourcesList(),
        client.recon(root),
        client.wire(root, true),
      ]);
      setTools(tools);
      setResources(resources);
      setScoutReport(scout);
      setWireReport(wire);
    } catch (e) {
      setError(String(e));
      setStatus("error");
    } finally {
      setScanning(false);
    }
  }

  const dist = scoutReport?.tier_distribution;
  const tiers: (Tier | "unknown")[] = ["a0", "a1", "a2", "a3", "a4", "unknown"];
  const total = dist ? Object.values(dist).reduce((s, n) => s + n, 0) : 0;
  const tierFiles =
    selectedTier && scoutReport
      ? scoutReport.symbols.filter((s) => s.tier === selectedTier)
      : [];
  const wireOk = wireReport && wireReport.violation_count === 0;
  const fileCount = scoutReport?.file_count ?? scoutReport?.python_file_count ?? 0;
  const autoFixable =
    wireReport?.autofixable_count ?? wireReport?.auto_fixable ?? "—";

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <ActionableCard delay={0}>
        <div
          data-testid="drop-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            setInputPath(e.dataTransfer.getData("text/plain") || inputPath);
          }}
          className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center"
        >
          <div className="flex items-center gap-2 flex-1 bg-cyber-dark border border-cyber-border px-3 py-2 focus-within:border-cyber-cyan transition-colors">
            <FolderSearch
              size={14}
              className="text-monolith-muted flex-shrink-0"
            />
            <input
              type="text"
              value={inputPath}
              onChange={(e) => setInputPath(e.target.value)}
              placeholder="Drop a folder or paste a path…"
              onKeyDown={(e) => e.key === "Enter" && handleScan()}
              className="flex-1 bg-transparent font-mono text-xs text-cyber-chrome placeholder:text-monolith-muted outline-none"
              aria-label="project path"
            />
          </div>
          <NeonButton
            onClick={handleScan}
            disabled={scanning || !inputPath.trim()}
            variant={scanning ? "success" : "cyan"}
          >
            {scanning ? "Scanning…" : "Scan"}
          </NeonButton>
        </div>
      </ActionableCard>

      {scoutReport && dist && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {(
              [
                ["Files", fileCount, FolderSearch, "text-cyber-cyan"],
                ["Symbols", scoutReport.symbol_count, Zap, "text-indigo-400"],
                [
                  "Violations",
                  wireReport?.violation_count ?? "—",
                  AlertTriangle,
                  wireOk ? "text-cyber-success" : "text-cyber-alert",
                ],
                ["Auto-fix", autoFixable, Wrench, "text-amber-400"],
              ] as [string, number | string, React.ElementType, string][]
            ).map(([label, value, Icon, color], i) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.05 * i }}
                className="bg-cyber-panel border border-cyber-border p-4 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-5 h-5 border-t border-r border-transparent group-hover:border-cyber-cyan transition-all duration-500" />
                <div className={`text-2xl font-mono font-bold ${color}`}>
                  {value}
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <Icon size={10} className="text-monolith-muted" />
                  <span className="text-[9px] font-mono uppercase tracking-widest text-monolith-muted">
                    {label}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>

          {wireReport && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className={`border px-5 py-3 flex items-center justify-between font-mono text-[11px] uppercase tracking-widest ${
                wireOk
                  ? "border-cyber-success/40 bg-cyber-success/5 text-cyber-success"
                  : "border-cyber-alert/40 bg-cyber-alert/5 text-cyber-alert"
              }`}
            >
              <span>
                {wireOk
                  ? "⬡ Wire: PASS — all imports legal"
                  : `⬡ Wire: FAIL — ${wireReport.violation_count} violation${
                      wireReport.violation_count !== 1 ? "s" : ""
                    }`}
              </span>
              {!wireOk && (
                <div className="flex gap-3 text-[9px]">
                  {(["F004", "F003", "other"] as const).map((cat) => {
                    const cnt = wireReport.violations.filter((v) =>
                      cat === "other"
                        ? !v.f_code?.startsWith("F004") && !v.f_code?.startsWith("F003")
                        : v.f_code?.startsWith(cat),
                    ).length;
                    if (!cnt) return null;
                    const clr =
                      cat === "F004"
                        ? "text-cyber-alert"
                        : cat === "F003"
                          ? "text-amber-400"
                          : "text-blue-400";
                    return (
                      <span key={cat} className={clr}>
                        {cat}× {cnt}
                      </span>
                    );
                  })}
                </div>
              )}
            </motion.div>
          )}

          <ActionableCard title="Tier Distribution" delay={0.1}>
            <div className="space-y-3">
              {tiers.map((tier) => {
                const count = dist[tier as keyof typeof dist] ?? 0;
                const pct = total > 0 ? (count / total) * 100 : 0;
                const isSelected = selectedTier === tier;
                return (
                  <div
                    key={tier}
                    className={`flex items-center gap-3 cursor-pointer transition-opacity ${
                      selectedTier && !isSelected ? "opacity-40" : "opacity-100"
                    }`}
                    onClick={() =>
                      setSelectedTier(isSelected ? null : (tier as Tier))
                    }
                    role="button"
                    aria-label={`tier ${tier}: ${count} symbols`}
                  >
                    <span
                      className="w-28 font-mono text-[10px] uppercase tracking-wide flex-shrink-0"
                      style={{ color: TC[tier] }}
                    >
                      {TL[tier]}
                    </span>
                    <div className="flex-1 bg-cyber-dark border border-cyber-border h-3 overflow-hidden">
                      <motion.div
                        data-testid={`tier-bar-${tier}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className="h-full"
                        style={{ background: TC[tier] }}
                      />
                    </div>
                    <span className="w-8 font-mono text-[10px] text-monolith-muted text-right">
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          </ActionableCard>

          {selectedTier && (
            <ActionableCard
              title={`${TL[selectedTier]} — ${tierFiles.length} symbols`}
              delay={0.15}
            >
              <div className="max-h-60 overflow-y-auto">
                {tierFiles.slice(0, 200).map((sym, i) => (
                  <div
                    key={i}
                    className="flex gap-3 px-3 py-1.5 border-b border-cyber-border text-[11px] font-mono"
                  >
                    <span className="text-monolith-muted w-16 flex-shrink-0">
                      {sym.kind}
                    </span>
                    <span className="text-cyber-chrome">{sym.name}</span>
                    <span className="text-monolith-muted ml-auto truncate">
                      {sym.file}:{sym.line}
                    </span>
                  </div>
                ))}
              </div>
            </ActionableCard>
          )}

          {wireReport && wireReport.violations.length > 0 && (
            <ActionableCard
              title={`Wire Violations (${wireReport.violations.length})`}
              delay={0.2}
            >
              <div className="max-h-60 overflow-y-auto">
                {wireReport.violations.map((v, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-3 py-1.5 border-b border-cyber-border text-[11px] font-mono"
                  >
                    <span
                      className="w-14 flex-shrink-0 font-bold"
                      style={{
                        color: v.f_code?.startsWith("F004")
                          ? "#f43f5e"
                          : v.f_code?.startsWith("F003")
                            ? "#fbbf24"
                            : "#60a5fa",
                      }}
                    >
                      {v.f_code}
                    </span>
                    <span className="text-cyber-cyan">{v.from_tier}</span>
                    <span className="text-monolith-muted">→</span>
                    <span className="text-cyber-alert">{v.to_tier}</span>
                    <span className="text-monolith-muted ml-auto truncate">
                      {v.file}
                    </span>
                  </div>
                ))}
              </div>
            </ActionableCard>
          )}
        </>
      )}

      {!scoutReport && status !== "connecting" && (
        <div className="border border-dashed border-cyber-border h-40 flex items-center justify-center">
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
            Enter a project path and click scan
          </span>
        </div>
      )}
    </div>
  );
}
