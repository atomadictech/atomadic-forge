"use client";
import { motion } from "motion/react";
import { CyberCard } from "./CyberCard";
import { ExternalLink, Github, Globe } from "lucide-react";

export function InvestSection() {
  return (
    <section id="invest" className="relative py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">
            09 / Invest
          </span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        {/* Headline */}
        <div className="text-center mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="font-mono font-bold leading-tight mb-6"
            style={{ fontSize: "clamp(2rem, 5vw, 4rem)" }}
          >
            <span className="block text-cyber-chrome">From substrate</span>
            <span className="block text-cyber-cyan glow-cyan">to standard.</span>
          </motion.h2>
          <p className="font-mono text-[13px] text-monolith-mid max-w-2xl mx-auto leading-relaxed">
            Atomadic is opening its first round. The engineering risk is retired —
            the products are live, tested, and self-audited. The round funds distribution,
            ecosystem partnerships, and the first hires.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-12">
          {/* Use of funds */}
          <CyberCard accent="cyan" delay={0}>
            <div className="p-8">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-cyan mb-6">
                Use of Investment
              </div>
              <div className="space-y-5">
                {[
                  {
                    area: "Engineering Hires",
                    desc: "Senior systems engineers to expand polyglot support (Rust, Go, Java, C++) and harden the AAAA-Nexus inference layer.",
                    color: "text-cyber-cyan",
                  },
                  {
                    area: "Go-to-Market",
                    desc: "Developer relations, ecosystem partnerships, conference presence, and category-defining content.",
                    color: "text-cyber-gold",
                  },
                  {
                    area: "Enterprise Readiness",
                    desc: "SOC 2, dedicated tenancy, audit-log retention, EU AI Act / FDA PCCP / NIST SR 11-7 conformance pipelines.",
                    color: "text-cyber-success",
                  },
                  {
                    area: "Ecosystem Integrations",
                    desc: "JetBrains, Neovim, Helix LSP integrations · GitHub App marketplace · deeper MCP coverage across major coding agents.",
                    color: "text-violet-400",
                  },
                ].map((u) => (
                  <div key={u.area} className="border-l-2 pl-4" style={{ borderColor: "currentColor" }}>
                    <div className={`font-mono text-[10px] font-bold mb-1 ${u.color}`}>{u.area}</div>
                    <p className="font-mono text-[10px] text-monolith-mid leading-relaxed">
                      {u.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </CyberCard>

          {/* Why now */}
          <CyberCard accent="gold" delay={0.1}>
            <div className="p-8">
              <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-gold mb-6">
                Why Now
              </div>
              <div className="space-y-4">
                {[
                  "AI coding token costs doubled in a week — Claude Code: $6→$13/day average, $30/day at the 90th percentile. Lang's 3.48× density translates directly to cost reduction at every billable token.",
                  "$7.65B AI coding market in 2025, projected $70.55B by 2034 at 27.57% CAGR.",
                  "MCP protocol vulnerability (CVE-2025-6514) affects 200,000+ servers. AAAA-Nexus's RatchetGate is a mathematically-proven mitigation.",
                  "80% of AI-generated codebases carry architectural anti-patterns within 30 days. Forge prevents them at generation time, not after.",
                  "The IR-for-agents category is unclaimed in the 2026 literature. Atomadic Lang holds the combination first: BPE custom vocab + 5-tier discipline + byte-identical round-trip + sub-μs edge decoding.",
                  "Regulatory compliance windows close in 2026: EU AI Act (Aug 2), CMMC-AI (Nov 10). Conformity Statement CS-1 is the only audit-ready receipt format in the wild.",
                ].map((w, i) => (
                  <div key={i} className="flex items-start gap-3 font-mono text-[11px]">
                    <span className="text-cyber-gold mt-0.5">▸</span>
                    <span className="text-monolith-mid leading-relaxed">{w}</span>
                  </div>
                ))}
              </div>
            </div>
          </CyberCard>
        </div>

        {/* Contact */}
        <div className="border border-cyber-cyan/30 bg-cyber-cyan/5 p-8 md:p-12 text-center mb-12">
          <div className="font-mono text-[9px] uppercase tracking-[0.4em] text-cyber-cyan mb-6">
            Contact
          </div>
          <h3 className="font-mono font-bold text-2xl text-cyber-chrome mb-4">
            invest@atomadic.tech
          </h3>
          <p className="font-mono text-[12px] text-monolith-mid mb-8 max-w-lg mx-auto leading-relaxed">
            Investor inquiries, partnership proposals, and acquihire conversations.
            Decks, financial model, and deeper technical briefings available on request.
          </p>
          <a
            href="mailto:invest@atomadic.tech?subject=Atomadic Investment Inquiry"
            className="inline-block border border-cyber-cyan text-cyber-cyan font-mono text-[11px] uppercase tracking-[0.3em] px-8 py-3 hover:bg-cyber-cyan hover:text-black transition-colors"
          >
            Open conversation
          </a>
        </div>

        {/* Secondary contact */}
        <div className="flex flex-wrap items-center justify-center gap-8 mb-12 font-mono text-[9px] uppercase tracking-widest">
          {[
            { label: "invest@atomadic.tech", href: "mailto:invest@atomadic.tech" },
            { label: "help@atomadic.tech", href: "mailto:help@atomadic.tech" },
            { label: "info@atomadic.tech", href: "mailto:info@atomadic.tech" },
          ].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="text-monolith-mid hover:text-cyber-cyan transition-colors"
            >
              {label}
            </a>
          ))}
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center justify-center gap-6">
          {[
            { label: "GitHub", href: "https://github.com/atomadictech/atomadic-forge", Icon: Github },
            { label: "PyPI", href: "https://pypi.org/project/atomadic-forge/", Icon: ExternalLink },
            { label: "forge.atomadic.tech", href: "https://forge.atomadic.tech", Icon: Globe },
            { label: "hello.atomadic.tech", href: "https://hello.atomadic.tech", Icon: Globe },
          ].map(({ label, href, Icon }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-monolith-mid hover:text-cyber-cyan transition-colors"
            >
              <Icon size={12} />
              {label}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
