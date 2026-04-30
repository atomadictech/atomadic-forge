"use client";
import { motion, useInView } from "motion/react";
import { useRef } from "react";
import { CyberCard } from "./CyberCard";

const BARS = [
  { label: "Pre-AI baseline",       pct: 5,  color: "#10b981", year: "2022" },
  { label: "12 months post-LLM",    pct: 28, color: "#f59e0b", year: "2023" },
  { label: "24 months post-LLM",    pct: 47, color: "#f97316", year: "2024" },
  { label: "Current (2025–26)",      pct: 60, color: "#f43f5e", year: "2026" },
];

function DriftBar({ label, pct, color, year, delay }: typeof BARS[0] & { delay: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  return (
    <div ref={ref} className="flex items-center gap-3">
      <span className="font-mono text-[9px] text-monolith-mid w-7 flex-shrink-0 text-right">{year}</span>
      <div className="flex-1 bg-cyber-border h-6 overflow-hidden relative">
        <motion.div
          initial={{ width: 0 }}
          animate={inView ? { width: `${pct}%` } : {}}
          transition={{ duration: 1, delay, ease: "easeOut" }}
          className="h-full flex items-center justify-end pr-2"
          style={{ background: color }}
        >
          <span className="font-mono text-[9px] font-bold text-black">{pct}%</span>
        </motion.div>
      </div>
      <span className="font-mono text-[9px] text-monolith-mid w-44 flex-shrink-0">{label}</span>
    </div>
  );
}

export function ProblemSection() {
  return (
    <section id="problem" className="relative py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section label */}
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">01 / The Problem</span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="grid md:grid-cols-2 gap-16 items-start">
          <div>
            <h2 className="font-mono font-bold text-3xl md:text-4xl text-cyber-chrome mb-6 leading-tight">
              AI writes code faster than humans can maintain it.
            </h2>
            <p className="font-mono text-[13px] text-monolith-mid leading-relaxed mb-6">
              Every major AI coding assistant — GitHub Copilot, Cursor, Claude Code, Devin — generates
              code without any understanding of your project&apos;s architectural contract. The code works
              today. It drifts tomorrow.
            </p>
            <p className="font-mono text-[13px] text-cyber-chrome leading-relaxed mb-8">
              Industry analysis found architectural anti-patterns in{" "}
              <span className="text-cyber-alert font-bold">80% of AI-generated codebases</span>, with
              repository-pattern violations jumping from 5% to 60% within 24 months of LLM adoption.
            </p>

            <div className="space-y-1 mb-8">
              {BARS.map((b, i) => (
                <DriftBar key={b.year} {...b} delay={0.2 + i * 0.15} />
              ))}
              <p className="font-mono text-[8px] text-monolith-mid mt-2">
                Repository-pattern violations in codebases post-LLM adoption · NITR 2026 / Agiflow 2025
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <CyberCard accent="alert" delay={0.1}>
              <div className="p-6">
                <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-alert mb-3">The NITR Benchmark</div>
                <div className="font-mono font-bold text-4xl text-cyber-alert mb-2">4.3%</div>
                <p className="font-mono text-[11px] text-monolith-mid leading-relaxed">
                  The best AI coding systems succeed at dependency control in multi-step architectural edits
                  only 4.3% of the time. The hardest challenge in the NITR benchmark — and the one that
                  matters most for long-term codebase health.
                </p>
              </div>
            </CyberCard>

            <CyberCard accent="alert" delay={0.2}>
              <div className="p-6">
                <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-alert mb-3">Architectural Edits Success Rate</div>
                <div className="font-mono font-bold text-4xl text-cyber-alert mb-2">20.6%</div>
                <p className="font-mono text-[11px] text-monolith-mid leading-relaxed">
                  Even the most capable AI systems succeed at maintainable, multi-step architectural edits
                  only 1 in 5 times. The speed of generation masks the debt being created.
                </p>
              </div>
            </CyberCard>

            <CyberCard accent="gold" delay={0.3}>
              <div className="p-6">
                <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-gold mb-3">The Gap</div>
                <p className="font-mono text-[12px] text-cyber-chrome leading-relaxed">
                  Governance and refactoring tools are <span className="text-cyber-gold">reactive</span> — they fix
                  symptoms after the fact. AI coding assistants are <span className="text-cyber-gold">generative</span> but
                  architecturally blind. <span className="text-cyber-chrome font-bold">Nothing sits between them</span> to
                  prevent the drift before it accumulates.
                </p>
              </div>
            </CyberCard>
          </div>
        </div>
      </div>
    </section>
  );
}
