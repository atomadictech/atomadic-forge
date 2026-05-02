import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ShieldCheck, FileSignature, AlertCircle } from "lucide-react";
import { useForgeStore } from "../store";
import { useForgeClient } from "../client/context";
import { ActionableCard } from "./ui/ActionableCard";
import { NeonButton } from "./ui/NeonButton";
import { ScoreGauge } from "./ui/ScoreGauge";
import type { Receipt } from "../types";

export function CertifyDashboard() {
  const {
    projectRoot,
    certifyResult,
    receipt,
    setCertifyResult,
    setReceipt,
    setError,
  } = useForgeStore();
  const client = useForgeClient();
  const [running, setRunning] = useState(false);
  const [emitReceipt, setEmitReceipt] = useState(false);
  const [localSign, setLocalSign] = useState(false);
  // Certify runs on the project root, which may differ from the scan source path.
  // Default: walk up from source path to find the repo/package root.
  const [certifyRoot, setCertifyRoot] = useState<string>("");

  // When projectRoot changes, default certifyRoot to it (user can override).
  useEffect(() => {
    if (projectRoot && !certifyRoot) setCertifyRoot(projectRoot);
  }, [projectRoot]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCertify() {
    const root = certifyRoot.trim() || projectRoot;
    if (!root) {
      setError("scan a project first");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const result = await client.certify(root, {
        emitReceipt,
        localSign,
      });
      setCertifyResult(result);
      if (emitReceipt) {
        const r = await client.receipt(root);
        setReceipt(r);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  // refresh existing receipt when projectRoot changes
  useEffect(() => {
    if (!projectRoot) return;
    client
      .receipt(projectRoot)
      .then((r) => r && setReceipt(r))
      .catch(() => {});
  }, [projectRoot, client, setReceipt]);

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <ActionableCard delay={0}>
        <div className="mb-4">
          <div className="flex items-center gap-2 text-cyber-cyan mb-2">
            <ShieldCheck size={14} />
            <h2 className="font-mono text-[11px] uppercase tracking-[0.3em]">
              Conformance Certify
            </h2>
          </div>
          <p className="font-mono text-[9px] text-monolith-muted mb-3">
            Score: documentation · tests · tier layout · upward imports
          </p>
          <div className="flex items-center gap-2 bg-cyber-dark border border-cyber-border px-3 py-2 focus-within:border-cyber-cyan transition-colors">
            <ShieldCheck size={12} className="text-monolith-muted flex-shrink-0" />
            <input
              type="text"
              value={certifyRoot}
              onChange={(e) => setCertifyRoot(e.target.value)}
              placeholder="Project root path (defaults to scan path)…"
              onKeyDown={(e) => e.key === "Enter" && !running && handleCertify()}
              className="flex-1 bg-transparent font-mono text-xs text-cyber-chrome placeholder:text-monolith-muted outline-none"
              aria-label="certify path"
            />
          </div>
          <p className="font-mono text-[8px] text-monolith-muted mt-1">
            Tip: certify on the repo root (where README/CHANGELOG/.github live) to score docs + CI checks.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between">
          <div />
          <div className="flex flex-col gap-2 sm:items-end">
            <label className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-monolith-muted">
              <input
                type="checkbox"
                checked={emitReceipt}
                onChange={(e) => setEmitReceipt(e.target.checked)}
                className="accent-cyber-cyan"
              />
              Emit receipt
            </label>
            <label className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-monolith-muted">
              <input
                type="checkbox"
                checked={localSign}
                onChange={(e) => setLocalSign(e.target.checked)}
                disabled={!emitReceipt}
                className="accent-cyber-cyan"
              />
              Sign locally (ed25519)
            </label>
            <NeonButton
              onClick={handleCertify}
              disabled={running || !(certifyRoot.trim() || projectRoot)}
              variant={running ? "success" : "cyan"}
            >
              {running ? "Certifying…" : "Run Certify"}
            </NeonButton>
          </div>
        </div>
      </ActionableCard>

      {certifyResult && (
        <ActionableCard title={`Score · ${certifyResult.score}/100`} delay={0.1}>
          <div className="flex flex-col md:flex-row items-center gap-8">
            <ScoreGauge score={Math.round(certifyResult.score)} label="Score" />
            <div className="flex-1 grid grid-cols-2 gap-3">
              {(
                [
                  ["Documentation", certifyResult.documentation_complete],
                  ["Tests present", certifyResult.tests_present],
                  ["Tier layout", certifyResult.tier_layout_present],
                  ["No upward imports", certifyResult.no_upward_imports],
                ] as [string, boolean][]
              ).map(([label, ok]) => (
                <div
                  key={label}
                  className={`bg-cyber-dark border px-4 py-3 ${
                    ok
                      ? "border-cyber-success/30 text-cyber-success"
                      : "border-cyber-alert/30 text-cyber-alert"
                  }`}
                >
                  <div className="font-mono font-bold text-sm">
                    {ok ? "PASS" : "FAIL"}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-monolith-muted mt-0.5">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {certifyResult.issues.length > 0 && (
            <div className="mt-5 border-t border-cyber-border pt-4">
              <div className="font-mono text-[10px] uppercase tracking-widest text-cyber-alert mb-2 flex items-center gap-2">
                <AlertCircle size={11} />
                Issues ({certifyResult.issues.length})
              </div>
              <ul className="space-y-1">
                {certifyResult.issues.map((issue, i) => (
                  <li
                    key={i}
                    className="font-mono text-[11px] text-monolith-gray pl-3 border-l border-cyber-alert/30"
                  >
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </ActionableCard>
      )}

      {receipt && <ReceiptPanel receipt={receipt} />}
    </div>
  );
}

function ReceiptPanel({ receipt }: { receipt: Receipt }) {
  const verdictColor: Record<string, string> = {
    PASS: "text-cyber-success border-cyber-success/40 bg-cyber-success/5",
    FAIL: "text-cyber-alert border-cyber-alert/40 bg-cyber-alert/5",
    REFINE: "text-amber-400 border-amber-400/40 bg-amber-400/5",
    QUARANTINE: "text-cyber-alert border-cyber-alert/40 bg-cyber-alert/5",
  };
  const v = verdictColor[receipt.verdict] ?? verdictColor.FAIL;

  return (
    <ActionableCard
      title={`Receipt · ${receipt.schema_version}`}
      delay={0.2}
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={`border px-5 py-3 mb-4 flex items-center gap-3 font-mono text-[11px] uppercase tracking-widest ${v}`}
      >
        <FileSignature size={14} />
        <span>Verdict: {receipt.verdict}</span>
        <span className="ml-auto text-[9px] text-monolith-muted normal-case tracking-normal">
          forge {receipt.forge_version}
        </span>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-[11px]">
        <KV label="project" value={receipt.project.name} />
        <KV label="root" value={receipt.project.root} />
        <KV
          label="language"
          value={receipt.project.language ?? "—"}
        />
        <KV
          label="symbols"
          value={String(receipt.scout.symbol_count)}
        />
        <KV label="wire" value={receipt.wire.verdict} />
        <KV
          label="wire violations"
          value={String(receipt.wire.violation_count)}
        />
        <KV
          label="certify score"
          value={String(receipt.certify.score)}
        />
        <KV
          label="signature"
          value={
            receipt.signatures.aaaa_nexus
              ? "AAAA-Nexus"
              : receipt.signatures.local_ed25519
                ? "local ed25519"
                : "unsigned"
          }
        />
      </div>
    </ActionableCard>
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
