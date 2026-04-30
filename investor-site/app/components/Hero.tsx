"use client";
import { motion } from "motion/react";
import { ArrowDown } from "lucide-react";

export function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center grid-bg hex-bg overflow-hidden px-6">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-cyber-cyan/[0.03] blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-cyber-gold/[0.02] blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 border border-cyber-cyan/30 bg-cyber-cyan/5 px-4 py-1.5 mb-12"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-cyber-cyan animate-pulse-slow" />
          <span className="font-mono text-[9px] uppercase tracking-[0.35em] text-cyber-cyan">
            Investor Overview · April 2026
          </span>
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="font-mono font-bold leading-[1.05] mb-8"
          style={{ fontSize: "clamp(2.6rem, 6.5vw, 5.5rem)" }}
        >
          <span className="block text-cyber-chrome">The architectural substrate</span>
          <span className="block text-cyber-cyan glow-cyan">for the agent economy.</span>
        </motion.h1>

        {/* Subline */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="font-mono text-[13px] md:text-[15px] text-monolith-mid max-w-2xl mx-auto leading-relaxed mb-3"
        >
          Eight connected products. One axiom. Built solo, off-grid in Cascadia, in two months.
          <span className="block mt-2 text-cyber-chrome">
            841 tests passing · 100/100 certify · 538 Lean4 theorems · 21 MCP tools.
          </span>
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.55 }}
          className="font-mono text-[10px] text-monolith-mid mb-16 tracking-wider uppercase"
        >
          No funding · One developer · Shipping
        </motion.p>

        {/* Four product pills */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7 }}
          className="flex flex-wrap items-center justify-center gap-3 mb-12"
        >
          {[
            { name: "Atomadic Forge", tag: "Architecture Compiler", color: "border-cyber-cyan text-cyber-cyan bg-cyber-cyan/5" },
            { name: "Atomadic Lang", tag: "Verified IR · .atm", color: "border-cyber-success text-cyber-success bg-cyber-success/5" },
            { name: "AAAA-Nexus", tag: "Verified Inference API", color: "border-cyber-gold text-cyber-gold bg-cyber-gold/5" },
            { name: "Atomadic", tag: "Sovereign AI Agent", color: "border-violet-400 text-violet-400 bg-violet-400/5" },
          ].map((p) => (
            <div key={p.name} className={`border font-mono text-[10px] px-4 py-2 ${p.color}`}>
              <span className="font-bold tracking-wide">{p.name}</span>
              <span className="ml-2 opacity-60 text-[9px] uppercase tracking-widest">{p.tag}</span>
            </div>
          ))}
        </motion.div>

        {/* Live link callout */}
        <motion.a
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.85 }}
          href="https://forge.atomadic.tech"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-3 border border-cyber-cyan/40 bg-cyber-cyan/5 px-5 py-2 mb-12 hover:bg-cyber-cyan/10 transition-colors group"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-cyber-success animate-pulse-slow" />
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-mid">Live now</span>
          <span className="font-mono text-[11px] text-cyber-cyan group-hover:text-cyber-chrome transition-colors">
            forge.atomadic.tech
          </span>
          <span className="font-mono text-[9px] text-monolith-mid">→ scan a repo · subscribe</span>
        </motion.a>

        {/* Quick stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1.0 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 max-w-2xl mx-auto border border-cyber-border bg-cyber-panel/50 p-6 mb-16"
        >
          {[
            { v: "841", label: "Tests Passing" },
            { v: "100/100", label: "Certify Score" },
            { v: "3.48×", label: "Lang Density" },
            { v: "1833+", label: "Live Cycles" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="font-mono font-bold text-2xl text-cyber-cyan">{s.v}</div>
              <div className="font-mono text-[8px] uppercase tracking-[0.25em] text-monolith-mid mt-1">{s.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Scroll cue */}
        <motion.a
          href="#problem"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.2 }}
          className="inline-flex flex-col items-center gap-2 text-monolith-mid hover:text-cyber-cyan transition-colors"
        >
          <span className="font-mono text-[9px] uppercase tracking-[0.3em]">Scroll to explore</span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          >
            <ArrowDown size={16} />
          </motion.div>
        </motion.a>
      </div>
    </section>
  );
}
