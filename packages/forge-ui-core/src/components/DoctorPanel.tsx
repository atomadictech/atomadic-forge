import { useEffect, useState } from "react";
import { Stethoscope, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { useForgeClient } from "../client/context";
import { ActionableCard } from "./ui/ActionableCard";
import { NeonButton } from "./ui/NeonButton";
import type { DoctorResult } from "../types";

export function DoctorPanel() {
  const client = useForgeClient();
  const [result, setResult] = useState<DoctorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setErr(null);
    try {
      const r = await client.doctor();
      setResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <ActionableCard delay={0}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-cyber-cyan">
            <Stethoscope size={14} />
            <h2 className="font-mono text-[11px] uppercase tracking-[0.3em]">
              Doctor
            </h2>
          </div>
          <NeonButton onClick={refresh} disabled={loading}>
            <span className="flex items-center gap-2">
              <RefreshCw
                size={11}
                className={loading ? "animate-spin" : ""}
              />
              Refresh
            </span>
          </NeonButton>
        </div>
      </ActionableCard>

      {err && (
        <div className="border border-cyber-alert/40 bg-cyber-alert/5 px-4 py-3 font-mono text-[11px] text-cyber-alert">
          {err}
        </div>
      )}

      {result && (
        <>
          <ActionableCard title="Environment" delay={0.1}>
            <div className="grid grid-cols-2 gap-3 font-mono text-[11px]">
              <KV label="forge" value={result.forge_version} />
              <KV label="python" value={result.python_version} />
            </div>
          </ActionableCard>

          <ActionableCard title="Optional Dependencies" delay={0.15}>
            <div className="space-y-2">
              {Object.entries(result.optional_deps).map(([name, dep]) => (
                <div
                  key={name}
                  className="flex items-center gap-3 px-3 py-2 border border-cyber-border bg-cyber-dark"
                >
                  {dep.installed ? (
                    <CheckCircle2
                      size={14}
                      className="text-cyber-success flex-shrink-0"
                    />
                  ) : (
                    <XCircle
                      size={14}
                      className="text-cyber-alert flex-shrink-0"
                    />
                  )}
                  <span className="font-mono text-[11px] text-cyber-chrome">
                    {name}
                  </span>
                  <span className="ml-auto font-mono text-[10px] text-monolith-muted">
                    {dep.installed ? (dep.version ?? "installed") : "missing"}
                  </span>
                </div>
              ))}
            </div>
          </ActionableCard>

          {result.warnings.length > 0 && (
            <ActionableCard title="Warnings" delay={0.2}>
              <ul className="space-y-1">
                {result.warnings.map((w, i) => (
                  <li
                    key={i}
                    className="font-mono text-[11px] text-amber-400 pl-3 border-l border-amber-400/30"
                  >
                    {w}
                  </li>
                ))}
              </ul>
            </ActionableCard>
          )}
        </>
      )}
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-cyber-dark border border-cyber-border px-3 py-2 flex justify-between gap-3">
      <span className="text-monolith-muted text-[9px] uppercase tracking-widest">
        {label}
      </span>
      <span className="text-cyber-chrome truncate">{value}</span>
    </div>
  );
}
