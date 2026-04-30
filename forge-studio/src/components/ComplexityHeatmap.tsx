import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { motion } from "motion/react";
import { useForgeStore } from "@/store";
import { ActionableCard } from "@/components/ui/ActionableCard";

interface FC { file: string; score: number; }

function stc(s: number): string {
  const r = s < 50 ? Math.round((s / 50) * 250) : 250;
  const g = s < 50 ? 200 : Math.round(200 - ((s - 50) / 50) * 150);
  return `rgb(${r},${g},60)`;
}

async function fetchComplexity(files: string[]): Promise<FC[]> {
  const results: FC[] = [];
  for (const file of files.slice(0, 100)) {
    try {
      const s = await invoke<number>("complexipy_score", { file });
      results.push({ file, score: Math.min(100, Math.max(0, s)) });
    } catch {
      throw new Error("complexipy unavailable");
    }
  }
  return results;
}

export function ComplexityHeatmap() {
  const { scoutReport } = useForgeStore();
  const [complexities, setComplexities] = useState<FC[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!scoutReport) return;
    const files = [...new Set(scoutReport.symbols.map((s) => s.file))].filter((f) => f.endsWith(".py"));
    if (files.length === 0) return;
    fetchComplexity(files).then(setComplexities).catch(() => setUnavailable(true));
  }, [scoutReport]);

  if (!scoutReport) {
    return (
      <div className="p-6 max-w-4xl">
        <ActionableCard title="Complexity Heatmap" delay={0}>
          <div className="h-40 flex items-center justify-center border border-dashed border-cyber-border">
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
              Scan a project to render the complexity heatmap
            </span>
          </div>
        </ActionableCard>
      </div>
    );
  }

  if (unavailable) {
    return (
      <div className="p-6 max-w-4xl">
        <ActionableCard title="Complexity Heatmap" delay={0}>
          <div className="border border-dashed border-cyber-border p-5 space-y-3">
            <p className="font-mono text-[10px] uppercase tracking-widest text-cyber-chrome">
              complexipy not installed
            </p>
            <p className="font-mono text-[9px] text-monolith-muted">Install for cognitive complexity overlay:</p>
            <code className="block bg-cyber-dark border border-cyber-border px-3 py-2 font-mono text-[11px] text-cyber-cyan">
              pip install complexipy
            </code>
          </div>
        </ActionableCard>
      </div>
    );
  }

  if (!complexities) {
    return (
      <div className="p-6 max-w-4xl">
        <ActionableCard title="Complexity Heatmap" delay={0}>
          <div className="h-40 flex items-center justify-center gap-3 font-mono text-[10px] uppercase tracking-widest text-monolith-muted">
            <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}>⟳</motion.span>
            Calculating cognitive complexity…
          </div>
        </ActionableCard>
      </div>
    );
  }

  const sorted = [...complexities].sort((a, b) => b.score - a.score);

  return (
    <div className="p-6 max-w-4xl">
      <ActionableCard title="Complexity Heatmap" delay={0}>
        <p className="font-mono text-[9px] uppercase tracking-widest text-monolith-muted mb-4">
          Cognitive complexity score per file — 0 = trivial · 100 = critical
        </p>
        <div
          data-testid="complexity-heatmap"
          className="grid gap-2"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))" }}
        >
          {sorted.map(({ file, score }, i) => {
            const short = file.split(/[/\\]/).slice(-2).join("/");
            return (
              <motion.div
                key={file}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.25, delay: i * 0.01 }}
                title={`${file} — score ${score}`}
                className="p-2.5 border border-white/10 font-mono text-[11px] overflow-hidden"
                style={{ background: stc(score), color: score > 60 ? "#fff" : "#0f172a" }}
              >
                <div className="font-bold text-sm leading-none mb-1">{score}</div>
                <div className="truncate opacity-80 text-[10px]">{short}</div>
              </motion.div>
            );
          })}
        </div>
      </ActionableCard>
    </div>
  );
}
