"use client";
import { CyberCard } from "./CyberCard";
import { StatCounter } from "./StatCounter";

export function MarketSection() {
  return (
    <section id="market" className="relative py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">06 / Market Opportunity</span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="text-center mb-20">
          <h2 className="font-mono font-bold text-3xl md:text-5xl text-cyber-chrome mb-6 leading-tight">
            A market growing faster<br />
            <span className="text-cyber-gold glow-gold">than anyone can govern it.</span>
          </h2>
          <p className="font-mono text-[13px] text-monolith-mid max-w-2xl mx-auto leading-relaxed">
            The AI coding tools market is in explosive consolidation. Three players own 70%+ of market share.
            None of them solve the architectural problem they create. That gap is Atomadic&apos;s opening.
          </p>
        </div>

        {/* Market size stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-20">
          <StatCounter value={7650000000} suffix="" prefix="$" label="Market Size 2025" sublabel="AI coding tools (millions)" color="text-cyber-cyan" />
          <StatCounter value={70550000000} prefix="$" label="Projected 2034" sublabel="At 27.57% CAGR" color="text-cyber-gold" />
          <StatCounter value={27} suffix="%" label="CAGR" sublabel="Compound annual growth rate" color="text-cyber-success" />
          <StatCounter value={70} suffix="%" label="Market Concentration" sublabel="Top 3 players' share" color="text-cyber-alert" />
        </div>

        {/* Competitive positioning */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          <CyberCard accent="cyan" delay={0}>
            <div className="p-6">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-cyan mb-4">
                Competitive Position
              </div>
              <h3 className="font-mono font-bold text-xl text-cyber-chrome mb-4">
                We don&apos;t compete with Copilot.<br />We solve the problem Copilot creates.
              </h3>
              <div className="space-y-3">
                {[
                  { label: "AI Coding Agents (Copilot, Cursor, Devin)", status: "generates", color: "text-cyber-alert" },
                  { label: "ArchUnit / Sonar / Linters",                status: "detects (post-hoc)", color: "text-cyber-gold" },
                  { label: "OpenRewrite / Moderne",                     status: "fixes (reactive)", color: "text-cyber-gold" },
                  { label: "Atomadic Forge",                            status: "prevents + enforces", color: "text-cyber-success" },
                ].map((r) => (
                  <div key={r.label} className="flex items-center gap-3 font-mono text-[10px]">
                    <span className={`w-24 flex-shrink-0 font-bold ${r.color}`}>{r.status}</span>
                    <span className="text-monolith-mid">{r.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </CyberCard>

          <CyberCard accent="gold" delay={0.1}>
            <div className="p-6">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-gold mb-4">
                The Unaddressed Niche
              </div>
              <h3 className="font-mono font-bold text-xl text-cyber-chrome mb-4">
                Proactive prevention of AI-generated architectural debt.
              </h3>
              <p className="font-mono text-[11px] text-monolith-mid leading-relaxed mb-4">
                Developers cannot manually review code at the speed AI generates it. The only viable
                solution is an automated architectural substrate that absorbs code and immediately
                enforces structure.
              </p>
              <div className="border border-cyber-gold/20 bg-cyber-gold/5 p-3">
                <p className="font-mono text-[10px] text-cyber-gold italic">
                  &ldquo;Atomadic Forge acts as a bridge — a deterministic, automated substrate that absorbs
                  code and restructures it to a maintainable standard immediately. A critical missing
                  piece in the AI development pipeline.&rdquo;
                </p>
                <p className="font-mono text-[9px] text-monolith-mid mt-2">— Independent market analysis, April 2026</p>
              </div>
            </div>
          </CyberCard>
        </div>

        {/* Token Cost Crisis */}
        <div className="border border-cyber-alert/30 bg-cyber-alert/5 p-8 mb-8">
          <div className="font-mono text-[9px] uppercase tracking-[0.4em] text-cyber-alert mb-4">
            The Token Cost Crisis — April 2026
          </div>
          <div className="grid md:grid-cols-3 gap-6 mb-6">
            {[
              { stat: "$13/day", label: "Avg Claude Code cost", note: "Doubled in one week" },
              { stat: "$30/day", label: "90th percentile cost", note: "Was $12 one week ago" },
              { stat: "3.48×",  label: "Lang density reduction", note: "Direct cost multiplier" },
            ].map((s) => (
              <div key={s.stat} className="text-center">
                <div className="font-mono font-bold text-2xl text-cyber-alert mb-1">{s.stat}</div>
                <div className="font-mono text-[10px] text-cyber-chrome mb-0.5">{s.label}</div>
                <div className="font-mono text-[9px] text-monolith-mid">{s.note}</div>
              </div>
            ))}
          </div>
          <p className="font-mono text-[11px] text-monolith-mid leading-relaxed">
            Enterprise shifted from flat-fee to per-token billing. Every major provider is expected to follow within
            six months. Developers report $500–$2,000/month in API costs. 60–80% of tokens are wasted on redundant
            output, repeated file reads, and noise data in a 30-minute session.{" "}
            <span className="text-cyber-chrome">Atomadic Lang&apos;s 3.48× compression addresses this directly — at enterprise scale (100+ developers),
            this represents millions in annual savings.</span>
          </p>
        </div>

        {/* Integration strategy */}
        <div className="border border-cyber-border bg-cyber-panel p-8">
          <h3 className="font-mono font-bold text-lg text-cyber-chrome mb-6 text-center">
            The Integrated Pipeline
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              {
                step: "01",
                title: "Structure",
                desc: "Forge enforces the 5-tier monadic law at generation time. Any AI agent, any codebase, one MCP config block.",
                color: "text-cyber-cyan",
              },
              {
                step: "02",
                title: "Compress & Verify",
                desc: "Lang lowers code to .atm IR — 3.48× denser, byte-identical round-trip, sub-μs constrained decoding for edge deployment.",
                color: "text-cyber-success",
              },
              {
                step: "03",
                title: "Trust",
                desc: "AAAA-Nexus returns Lean4-attested inference at $0.002/call. 538 theorems. CVE-2025-6514 mitigated. x402 micropayments.",
                color: "text-cyber-gold",
              },
              {
                step: "04",
                title: "Operate",
                desc: "Atomadic runs as sovereign AI on $5/month. The proof that all four layers work in production, today.",
                color: "text-violet-400",
              },
            ].map((s) => (
              <div key={s.step} className="flex flex-col gap-3">
                <div className={`font-mono font-bold text-3xl ${s.color} opacity-30`}>{s.step}</div>
                <h4 className={`font-mono font-bold text-sm ${s.color}`}>{s.title}</h4>
                <p className="font-mono text-[11px] text-monolith-mid leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
