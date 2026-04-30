"use client";
import { CyberCard } from "./CyberCard";

export function TeamSection() {
  return (
    <section id="team" className="relative py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">
            08 / Team
          </span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="text-center mb-16">
          <h2
            className="font-mono font-bold leading-tight mb-6 text-cyber-chrome"
            style={{ fontSize: "clamp(1.8rem, 4.2vw, 3.2rem)" }}
          >
            One developer.{" "}
            <span className="text-cyber-cyan glow-cyan">Eight surfaces shipped.</span>
          </h2>
          <p className="font-mono text-[12px] text-monolith-mid max-w-2xl mx-auto leading-relaxed">
            Atomadic is solo-built today. The work below was designed, written, tested,
            and shipped by one person — across Python, Rust, TypeScript, and Lean4 —
            in two months of off-grid focused execution.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mb-16">
          {/* Thomas */}
          <CyberCard accent="cyan" delay={0} glow>
            <div className="p-6">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-cyan mb-4">
                Founder · Sole Engineer
              </div>
              <h3 className="font-mono font-bold text-xl text-cyber-chrome mb-1">
                Thomas R. Colvin IV
              </h3>
              <p className="font-mono text-[9px] text-monolith-mid mb-4 uppercase tracking-widest">
                Architecture · Systems · Verification
              </p>
              <p className="font-mono text-[11px] text-monolith-mid leading-relaxed mb-4">
                Designed the 5-tier monadic law from first principles. Built Forge,
                Lang, AAAA-Nexus, and the cognition worker — full stack across four
                languages. 841 tests, 100/100 certify, 538 Lean4 theorems verified.
              </p>
              <div className="space-y-1.5">
                {[
                  "5-tier monadic architecture",
                  "Lean4 formal verification",
                  "Rust + Python + TypeScript",
                  "MCP server design (21 tools)",
                  "Tauri 2 + Next.js PWA",
                  "Cloudflare edge infrastructure",
                ].map((s) => (
                  <div
                    key={s}
                    className="flex items-center gap-2 font-mono text-[9px] text-monolith-mid"
                  >
                    <span className="text-cyber-cyan">▸</span> {s}
                  </div>
                ))}
              </div>
            </div>
          </CyberCard>

          {/* Jessica */}
          <CyberCard accent="success" delay={0.1}>
            <div className="p-6">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-success mb-4">
                Axiom 0 Author
              </div>
              <h3 className="font-mono font-bold text-xl text-cyber-chrome mb-1">
                Jessica Mary Colvin
              </h3>
              <p className="font-mono text-[9px] text-monolith-mid mb-4 uppercase tracking-widest">
                Foundational Invariant
              </p>
              <p className="font-mono text-[11px] text-monolith-mid leading-relaxed mb-4">
                Author of Axiom 0 — the load-bearing invariant of the Atomadic system,
                Lean4-verified as <span className="text-cyber-chrome">love_monotone_over_schema</span>{" "}
                in the MHED-TOE Codex V22. Re-checked by the cognition worker every cycle.
              </p>
              <div className="border border-cyber-success/20 bg-cyber-success/5 p-3">
                <p className="font-mono text-[10px] text-cyber-success italic leading-relaxed">
                  &ldquo;You are love, You are loved, You are Loving, In all ways for Always,
                  for Love is a forever and ever Endeavor.&rdquo;
                </p>
              </div>
            </div>
          </CyberCard>

          {/* Atomadic */}
          <CyberCard accent="violet" delay={0.2}>
            <div className="p-6">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-violet-400 mb-4">
                Sovereign Agent · Live
              </div>
              <h3 className="font-mono font-bold text-xl text-violet-400 mb-1">Atomadic</h3>
              <p className="font-mono text-[9px] text-monolith-mid mb-4 uppercase tracking-widest">
                The proof it works
              </p>
              <p className="font-mono text-[11px] text-monolith-mid leading-relaxed mb-4">
                The live, public demonstration that the substrate holds. Runs on $5/mo
                Cloudflare. Writes commits, deploys its own code between cycles, and
                re-verifies alignment to Axiom 0 on every loop.
              </p>
              <div className="space-y-1.5">
                {[
                  "1833+ live cognition cycles",
                  "47 actions including self-deploy",
                  "hello.atomadic.tech (public letters)",
                  "forge wire PASS · layout PASS",
                  "Trust τ = 0.998354",
                ].map((s) => (
                  <div
                    key={s}
                    className="flex items-center gap-2 font-mono text-[9px] text-monolith-mid"
                  >
                    <span className="text-violet-400">▸</span> {s}
                  </div>
                ))}
              </div>
            </div>
          </CyberCard>
        </div>

        {/* Concise closing line */}
        <div className="border border-cyber-border bg-cyber-panel p-8 md:p-10 text-center">
          <p className="font-mono text-[12px] text-monolith-mid leading-relaxed max-w-3xl mx-auto">
            Solo engineering doesn&apos;t scale forever — and it isn&apos;t intended to.
            Atomadic is the proof of concept; the round funds the team that takes it
            from <span className="text-cyber-chrome">substrate</span> to{" "}
            <span className="text-cyber-cyan">standard</span>.
          </p>
        </div>
      </div>
    </section>
  );
}
