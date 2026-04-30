"use client";
import { StatCounter } from "./StatCounter";
import { CyberCard } from "./CyberCard";

const METRICS = [
  { value: 841,   suffix: "",    label: "Tests Passing",     sublabel: "Python + TypeScript",     color: "text-cyber-success" },
  { value: 100,   suffix: "/100",label: "Certify Score",     sublabel: "forge certify · self-audit", color: "text-cyber-cyan" },
  { value: 0,     suffix: "",    label: "Wire Violations",   sublabel: "Since v0.2.2 — every commit", color: "text-cyber-success" },
  { value: 21,    suffix: "",    label: "MCP Tools",         sublabel: "21 tools + 5 resources",  color: "text-cyber-cyan" },
  { value: 23487, suffix: "",    label: "Symbols Absorbed",  sublabel: "In single stress-test run", color: "text-cyber-gold" },
  { value: 538,   suffix: "",    label: "Lean4 Theorems",    sublabel: "0 sorry — AAAA-Nexus corpus", color: "text-violet-400" },
  { value: 36,    suffix: "+",   label: "CLI Verbs",         sublabel: "forge absorb, wire, certify…", color: "text-cyber-chrome" },
  { value: 1833,  suffix: "+",   label: "Cognition Cycles",  sublabel: "Atomadic live cognition",  color: "text-violet-400" },
];

const MILESTONES = [
  { date: "Feb 2026",   label: "Project start",              note: "Solo, off-grid, no funding" },
  { date: "Mar 2026",   label: "v0.1.0 — core verbs",       note: "absorb, wire, certify, plan" },
  { date: "Mar 2026",   label: "AAAA-Nexus corpus complete", note: "538 Lean4 theorems, 0 sorry" },
  { date: "Apr 2026",   label: "v0.2.2 — 0 violations",     note: "forge wire PASS maintained since" },
  { date: "Apr 2026",   label: "Atomadic goes live",         note: "1833+ cycles, $5/mo infrastructure" },
  { date: "Apr 2026",   label: "v0.3.0 — polyglot + MCP",   note: "JS/TS support, 21 MCP tools, VS Code" },
  { date: "Apr 2026",   label: "v0.3.2 — Forge Studio",     note: "Tauri 2 GUI, cyberpunk UI, 841 tests" },
  { date: "Apr 2026",   label: "v0.3.2 — Forge Studio",     note: "841 tests · 0 violations · 100/100" },
  { date: "Now",        label: "Seeking investment",         note: "PyPI live · GitHub public · MCP ready" },
];

export function TractionSection() {
  return (
    <section id="traction" className="relative py-32 px-6 bg-cyber-panel/30">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">07 / Traction</span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="text-center mb-16">
          <h2 className="font-mono font-bold text-3xl md:text-4xl text-cyber-chrome mb-6 leading-tight">
            Shipped. Tested. Self-audited.<br />
            <span className="text-cyber-cyan">From a camper, in two months.</span>
          </h2>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12 mb-20">
          {METRICS.map((m) => (
            <StatCounter key={m.label} {...m} />
          ))}
        </div>

        {/* Timeline */}
        <CyberCard accent="cyan" delay={0}>
          <div className="p-8">
            <h3 className="font-mono font-bold text-lg text-cyber-chrome mb-8">Build Timeline</h3>
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-[88px] top-0 bottom-0 w-px bg-cyber-border" />
              <div className="space-y-6">
                {MILESTONES.map((m, i) => (
                  <div key={i} className="flex items-start gap-6">
                    <span className="font-mono text-[9px] text-monolith-mid w-20 flex-shrink-0 text-right pt-0.5">
                      {m.date}
                    </span>
                    <div
                      className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 z-10 ${
                        i === MILESTONES.length - 1
                          ? "bg-cyber-cyan shadow-[0_0_8px_#22d3ee]"
                          : "bg-cyber-border border border-cyber-border-bright"
                      }`}
                    />
                    <div>
                      <div className="font-mono text-[11px] font-bold text-cyber-chrome">{m.label}</div>
                      <div className="font-mono text-[9px] text-monolith-mid mt-0.5">{m.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CyberCard>

        {/* The self-audit */}
        <div className="mt-8 border border-cyber-success/20 bg-cyber-success/5 p-6">
          <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-success mb-3">
            Live Self-Audit — Atomadic Forge audits itself with every commit
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { cmd: "forge wire",    result: "PASS · 0 violations" },
              { cmd: "forge certify", result: "100/100" },
              { cmd: "forge layout",  result: "PASS" },
              { cmd: "forge docs",    result: "PASS" },
            ].map((r) => (
              <div key={r.cmd} className="bg-black border border-cyber-border p-3">
                <div className="font-mono text-[10px] text-cyber-cyan mb-1">$ {r.cmd}</div>
                <div className="font-mono text-[10px] text-cyber-success">{r.result}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
