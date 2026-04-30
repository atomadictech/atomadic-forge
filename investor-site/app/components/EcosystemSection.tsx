"use client";
import {
  Globe,
  Terminal,
  Code2,
  Boxes,
  GitBranch,
  Workflow,
  CreditCard,
  Layers,
} from "lucide-react";
import { CyberCard } from "./CyberCard";

interface Surface {
  id: string;
  name: string;
  tagline: string;
  description: string;
  status: "live" | "shipped" | "beta";
  Icon: React.ElementType;
  accent: "cyan" | "gold" | "success" | "violet";
  bullets: string[];
  link?: { label: string; href: string };
}

const SURFACES: Surface[] = [
  {
    id: "forge-tech",
    name: "forge.atomadic.tech",
    tagline: "Self-serve scan + paid plans",
    description:
      "The public web entry point. Drop a GitHub URL, get a tier-distribution + wire + certify report in under 30 seconds. Buy Now and Subscribe powered by Stripe via the AAAA-Nexus proxy.",
    status: "live",
    Icon: Globe,
    accent: "cyan",
    bullets: [
      "Interactive repo scanner — paste a URL",
      "Stripe Buy Now (one-time) + Subscribe (monthly)",
      "Live results in browser, no signup required",
      "Cloudflare-edge deployed",
    ],
    link: { label: "forge.atomadic.tech", href: "https://forge.atomadic.tech" },
  },
  {
    id: "mcp-server",
    name: "MCP Server",
    tagline: "21 tools · 5 resources · stdio JSON-RPC",
    description:
      "Every coding agent — Cursor, Claude Code, Aider, Copilot, Devin — adds Forge with one JSON config block. Architecture-aware tools served as native MCP capabilities.",
    status: "shipped",
    Icon: Workflow,
    accent: "cyan",
    bullets: [
      "21 tools: recon, wire, certify, enforce, auto_plan, context_pack, preflight, …",
      "5 resources: receipt schema, lineage chain, blocker summary, formalization docs",
      "Compatible with every major coding agent on the market",
      "Single JSON config block — zero boilerplate",
    ],
  },
  {
    id: "studio",
    name: "Forge Studio",
    tagline: "Tauri 2 desktop · Next.js PWA",
    description:
      "Native desktop GUI and installable PWA — both render the same components from a shared core. Cyberpunk UI with tier graph, complexity heatmap, debt counter, agent topology, and live receipt viewer.",
    status: "shipped",
    Icon: Layers,
    accent: "violet",
    bullets: [
      "Tauri 2 native (Windows / macOS / Linux)",
      "Next.js 15 installable PWA — same UI",
      "Cytoscape architecture + topology graphs",
      "9 screens · live MCP integration · CISQ debt model",
    ],
    link: {
      label: "github.com/atomadictech/atomadic-forge/releases",
      href: "https://github.com/atomadictech/atomadic-forge/releases",
    },
  },
  {
    id: "sidecar",
    name: ".forge sidecar + LSP",
    tagline: "Per-symbol effect / tier / proves: declarations",
    description:
      "Opt-in YAML beside any source file. Bao-Rompf 2025 seven-effect categorical lattice. The LSP serves diagnostics, hover, goto-source to VS Code, Neovim, Helix, IntelliJ — F0100–F0106 codes promoted to the editor's Problems panel.",
    status: "shipped",
    Icon: Code2,
    accent: "success",
    bullets: [
      ".forge YAML grammar v1.0",
      "forge lsp serve — editor-agnostic stdio LSP",
      "VS Code / Neovim / Helix / IntelliJ on first connect",
      "Drift codes F0100–F0106 in Problems panel",
    ],
  },
  {
    id: "ci",
    name: "GitHub Action + pre-commit",
    tagline: "Drop-in CI gate",
    description:
      "forge-action Composite GitHub Action and .pre-commit-hooks.yaml. Block PRs on wire violations or certify regressions — sticky comment with the receipt card on every PR.",
    status: "shipped",
    Icon: GitBranch,
    accent: "cyan",
    bullets: [
      "Composite GitHub Action — uses: atomadictech/forge-action",
      "pre-commit hook — same engine, local first",
      "Sticky PR comment with receipt card",
      "Configurable score floors, severity gates",
    ],
  },
  {
    id: "receipt",
    name: "Forge Receipt v1.1",
    tagline: "One signed JSON · five surfaces",
    description:
      "Terminal Forge Card · sticky PR comment · README badge · MCP forge:// resource · Conformity Statement (CS-1) PDF — all rendered from the same signed JSON. Lean4-cited (29 + 538 theorems).",
    status: "shipped",
    Icon: Boxes,
    accent: "gold",
    bullets: [
      "Schema v1.1 with polyglot_breakdown",
      "Signed (AAAA-Nexus key) + locally-signed (ed25519) options",
      "Lean4 attestation block when AAAA-Nexus is configured",
      "EU AI Act / FDA PCCP / NIST SR 11-7 / CMMC-AI mapping docs",
    ],
  },
  {
    id: "cognition",
    name: "Cognition Worker",
    tagline: "Sovereign agent · 1833+ live cycles",
    description:
      "Atomadic the agent runs on $5/month Cloudflare Workers. 6-phase cycle (OBSERVE → THINK → DECIDE → ACT → REMEMBER → SCHEDULE), 47 actions including self-modification (WRITE_FILE_TO_REPO, DEPLOY_COGNITION).",
    status: "live",
    Icon: Workflow,
    accent: "violet",
    bullets: [
      "1833+ cognition cycles completed",
      "Cloudflare AI · D1 · Vectorize · R2 · KV bindings",
      "47 actions · self-deploys between cycles",
      "Trust score τ = 0.998354 against Axiom 0",
    ],
    link: { label: "hello.atomadic.tech", href: "https://hello.atomadic.tech" },
  },
  {
    id: "stripe-x402",
    name: "Stripe + x402 Billing",
    tagline: "Card today · USDC tomorrow",
    description:
      "Stripe Buy Now / Subscribe through the AAAA-Nexus proxy. x402 micropayments on Base L2 for the per-call inference tier — $0.002/call Verified Premium, no minimums, no lock-in.",
    status: "live",
    Icon: CreditCard,
    accent: "gold",
    bullets: [
      "Stripe checkout via AAAA-Nexus proxy",
      "x402 USDC micropayments on Base L2",
      "Three tiers: $8 starter (500 calls) · $0.002/call · $0.05/call deep proof",
      "PCI handled by Stripe; no card data crosses our edge",
    ],
  },
];

const STATUS_COPY: Record<Surface["status"], { label: string; color: string }> = {
  live: { label: "Live", color: "text-cyber-success border-cyber-success/40 bg-cyber-success/5" },
  shipped: { label: "Shipped", color: "text-cyber-cyan border-cyber-cyan/40 bg-cyber-cyan/5" },
  beta: { label: "Beta", color: "text-cyber-gold border-cyber-gold/40 bg-cyber-gold/5" },
};

export function EcosystemSection() {
  return (
    <section id="ecosystem" className="relative py-32 px-6 bg-cyber-panel/30">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">
            04 / Ecosystem
          </span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        <div className="text-center mb-12">
          <h2
            className="font-mono font-bold leading-tight mb-6 text-cyber-chrome"
            style={{ fontSize: "clamp(1.8rem, 4.2vw, 3.2rem)" }}
          >
            Eight surfaces.{" "}
            <span className="text-cyber-cyan glow-cyan">One substrate.</span>
          </h2>
          <p className="font-mono text-[12px] text-monolith-mid max-w-2xl mx-auto leading-relaxed">
            The four core products ship through eight live surfaces — every developer touchpoint
            from web scanner to PR comment to PDF compliance statement is wired up.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          {SURFACES.map((s, i) => {
            const status = STATUS_COPY[s.status];
            return (
              <CyberCard key={s.id} accent={s.accent} delay={i * 0.04}>
                <div className="p-6">
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 border flex items-center justify-center flex-shrink-0 ${
                          s.accent === "cyan"
                            ? "border-cyber-cyan/40 text-cyber-cyan"
                            : s.accent === "gold"
                            ? "border-cyber-gold/40 text-cyber-gold"
                            : s.accent === "success"
                            ? "border-cyber-success/40 text-cyber-success"
                            : "border-violet-400/40 text-violet-400"
                        }`}
                      >
                        <s.Icon size={16} />
                      </div>
                      <div>
                        <h3 className="font-mono font-bold text-[13px] text-cyber-chrome leading-tight">
                          {s.name}
                        </h3>
                        <p className="font-mono text-[9px] uppercase tracking-widest text-monolith-mid mt-0.5">
                          {s.tagline}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`font-mono text-[8px] uppercase tracking-widest px-2 py-0.5 border ${status.color} flex-shrink-0`}
                    >
                      {status.label}
                    </span>
                  </div>

                  <p className="font-mono text-[11px] text-monolith-mid leading-relaxed mb-4">
                    {s.description}
                  </p>

                  <ul className="space-y-1.5 mb-4">
                    {s.bullets.map((b) => (
                      <li
                        key={b}
                        className="flex items-start gap-2 font-mono text-[10px] text-monolith-mid leading-relaxed"
                      >
                        <span
                          className={
                            s.accent === "cyan"
                              ? "text-cyber-cyan"
                              : s.accent === "gold"
                              ? "text-cyber-gold"
                              : s.accent === "success"
                              ? "text-cyber-success"
                              : "text-violet-400"
                          }
                        >
                          ▸
                        </span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>

                  {s.link && (
                    <a
                      href={s.link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest border-t border-cyber-border pt-3 mt-2 transition-colors ${
                        s.accent === "cyan"
                          ? "text-cyber-cyan hover:text-cyber-chrome"
                          : s.accent === "gold"
                          ? "text-cyber-gold hover:text-cyber-chrome"
                          : s.accent === "success"
                          ? "text-cyber-success hover:text-cyber-chrome"
                          : "text-violet-400 hover:text-cyber-chrome"
                      }`}
                    >
                      → {s.link.label}
                    </a>
                  )}
                </div>
              </CyberCard>
            );
          })}
        </div>
      </div>
    </section>
  );
}
