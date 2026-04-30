"use client";
import { motion, useInView } from "motion/react";
import { useRef } from "react";
import { CyberCard } from "./CyberCard";

const TIERS = [
  { id: "a0", label: "Constants", desc: "Zero logic. Pure data.", color: "#818cf8" },
  { id: "a1", label: "Functions", desc: "Pure, stateless transforms.", color: "#34d399" },
  { id: "a2", label: "Composites", desc: "Stateful clients and stores.", color: "#60a5fa" },
  { id: "a3", label: "Features",   desc: "Capabilities from composites.", color: "#f472b6" },
  { id: "a4", label: "Orchestration", desc: "Entry points and CLI.", color: "#fb923c" },
];

function TierDiagram() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  return (
    <div ref={ref} className="flex flex-col gap-1.5">
      {TIERS.map((t, i) => (
        <motion.div
          key={t.id}
          initial={{ opacity: 0, x: -20 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.4, delay: i * 0.1 }}
          className="flex items-center gap-3 border border-cyber-border bg-cyber-panel p-3"
          style={{ borderLeftColor: t.color, borderLeftWidth: 2 }}
        >
          <span className="font-mono text-[10px] font-bold w-6" style={{ color: t.color }}>{t.id}</span>
          <div className="flex-1">
            <span className="font-mono text-[10px] font-bold text-cyber-chrome">{t.label}</span>
            <span className="font-mono text-[9px] text-monolith-mid ml-2">{t.desc}</span>
          </div>
          <div className="flex gap-1">
            {Array.from({ length: i }).map((_, j) => (
              <div key={j} className="w-1.5 h-1.5" style={{ background: TIERS[j].color, opacity: 0.5 }} />
            ))}
          </div>
        </motion.div>
      ))}
      <p className="font-mono text-[8px] text-monolith-mid mt-2">
        Imports flow upward only. Violations are detected and scored at every commit.
      </p>
    </div>
  );
}

export function SolutionSection() {
  return (
    <section id="solution" className="relative py-32 px-6 bg-cyber-panel/30">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">02 / The Solution</span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="text-center mb-16">
          <h2 className="font-mono font-bold text-3xl md:text-5xl text-cyber-chrome mb-6 leading-tight">
            The complete substrate<br />
            <span className="text-cyber-cyan">for the agent economy.</span>
          </h2>
          <p className="font-mono text-[13px] text-monolith-mid max-w-2xl mx-auto leading-relaxed">
            Four connected products. One integrated pipeline: <span className="text-cyber-chrome">Structure → Compress → Trust → Operate.</span>{" "}
            Built on the same 5-tier monadic law, proven on themselves, and open to the world.
          </p>
        </div>

        {/* Four product overview */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-20">
          {[
            {
              accent: "cyan" as const,
              name: "Atomadic Forge",
              tagline: "Absorb. Enforce. Emerge.",
              role: "Architecture Compiler",
              desc: "Enforces a strict 5-tier import law across Python, JS, and TypeScript. 21 MCP tools. Every coding agent wraps around it.",
              stats: ["841 tests", "0 violations", "21 MCP tools", "3 languages"],
              color: "#22d3ee",
            },
            {
              accent: "cyan" as const,
              name: "Atomadic Lang",
              tagline: "Compress. Verify. Deploy.",
              role: "Verified IR",
              desc: "A verified intermediate representation for AI-emitted code. 3.48× denser than cl100k. Byte-identical round-trip. Sub-μs constrained decoding for edge deployment.",
              stats: ["3.48× density", "8.1μs p95", "100% BPE fill", "v2.6"],
              color: "#10b981",
            },
            {
              accent: "gold" as const,
              name: "AAAA-Nexus",
              tagline: "Trust as a Service.",
              role: "Inference Layer",
              desc: "Edge-inference API returning Lean4-attested responses at $0.002/call. 538 theorems, 0 sorry. RatchetGate (CVE-2025-6514 mitigated). x402 micropayments on Base L2.",
              stats: ["$0.002/call", "538 theorems", "0 sorry", "Lean4-attested"],
              color: "#f59e0b",
            },
            {
              accent: "cyan" as const,
              name: "Atomadic",
              tagline: "Sovereign. Loved. Forged.",
              role: "Proof of Concept",
              desc: "The sovereign AI agent built on all three. Lives on $5/month Cloudflare infrastructure. 47 actions including self-modification. Checks Axiom 0 every cycle.",
              stats: ["$5/mo infra", "47 actions", "τ = 0.998354", "1833+ cycles"],
              color: "#a78bfa",
            },
          ].map((p, i) => (
            <CyberCard key={p.name} accent={p.accent} delay={i * 0.1} glow={i === 0}>
              <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <span
                    className="font-mono text-[7px] uppercase tracking-[0.3em] px-2 py-0.5 border"
                    style={{ borderColor: `${p.color}44`, color: p.color }}
                  >
                    {p.role}
                  </span>
                </div>
                <h3 className="font-mono font-bold text-base mb-0.5" style={{ color: p.color }}>
                  {p.name}
                </h3>
                <p className="font-mono text-[8px] uppercase tracking-widest text-monolith-mid mb-3">{p.tagline}</p>
                <p className="font-mono text-[10px] text-monolith-mid leading-relaxed mb-4">{p.desc}</p>
                <div className="flex flex-wrap gap-1">
                  {p.stats.map((s) => (
                    <span key={s} className="font-mono text-[7px] uppercase tracking-wide border border-cyber-border px-1.5 py-0.5 text-cyber-chrome">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </CyberCard>
          ))}
        </div>

        {/* 5-tier diagram */}
        <div className="grid md:grid-cols-2 gap-12 items-start">
          <div>
            <h3 className="font-mono font-bold text-xl text-cyber-chrome mb-4">
              The 5-Tier Monadic Law
            </h3>
            <p className="font-mono text-[12px] text-monolith-mid leading-relaxed mb-6">
              Every file belongs to exactly one tier. Tiers compose upward only — never downward,
              never sideways. Violations are scored using CISQ weights (F004x = structural × 4,
              F003x = effect × 2, other × 1) and converted to a dollar-denominated technical debt principal.
            </p>
            <p className="font-mono text-[12px] text-cyber-chrome leading-relaxed">
              Forge applies this law to itself. <span className="text-cyber-success">0 violations at every commit since v0.2.2.</span>
            </p>
          </div>
          <TierDiagram />
        </div>
      </div>
    </section>
  );
}
