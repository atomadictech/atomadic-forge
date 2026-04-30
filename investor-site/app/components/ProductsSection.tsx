"use client";
import { CyberCard } from "./CyberCard";

export function ProductsSection() {
  return (
    <section id="products" className="relative py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-16">
          <div className="h-px flex-1 bg-cyber-border" />
          <span className="font-mono text-[9px] uppercase tracking-[0.4em] text-monolith-mid">03 / Products</span>
          <div className="h-px flex-1 bg-cyber-border" />
        </div>

        {/* PRODUCT 1: Forge */}
        <div className="mb-20">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-1 h-12 bg-cyber-cyan" />
            <div>
              <h2 className="font-mono font-bold text-2xl md:text-3xl text-cyber-cyan">Atomadic Forge</h2>
              <p className="font-mono text-[10px] uppercase tracking-widest text-monolith-mid">Absorb · Enforce · Emerge</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <p className="font-mono text-[13px] text-monolith-mid leading-relaxed mb-4">
                A polyglot (Python, JavaScript, TypeScript) architecture compiler and enforcement engine.
                It absorbs any codebase, maps it to the 5-tier monadic law, detects violations by import
                direction, scores them with CISQ weights, and outputs a signed receipt across 5 surfaces.
              </p>
              <p className="font-mono text-[13px] text-cyber-chrome leading-relaxed">
                The MCP server exposes 21 tools and 5 resources that any AI coding agent (Cursor, Claude Code,
                Aider, Copilot, Devin) can call directly. One JSON config block — any agent is now
                architecturally aware of your codebase.
              </p>
            </div>
            <div className="space-y-3">
              {[
                { label: "MCP server", desc: "21 tools, 5 resources — one JSON config" },
                { label: "VS Code extension", desc: "LSP integration, live violation highlighting" },
                { label: "CI/CD gate", desc: "GitHub Actions, blocks PR on violations" },
                { label: "Forge Studio", desc: "Tauri 2 desktop GUI, cyberpunk UI" },
                { label: ".forge sidecar", desc: "Per-symbol YAML: effect, tier, proves:" },
                { label: "Forge Receipt", desc: "Signed JSON across 5 surfaces including PyPI badge" },
              ].map((f) => (
                <div key={f.label} className="flex items-start gap-3 border-l-2 border-cyber-cyan/30 pl-3">
                  <div>
                    <div className="font-mono text-[10px] font-bold text-cyber-cyan">{f.label}</div>
                    <div className="font-mono text-[9px] text-monolith-mid">{f.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* MCP config snippet */}
          <div className="bg-black border border-cyber-border p-5 overflow-x-auto">
            <div className="font-mono text-[9px] text-monolith-mid mb-3">// Add to Cursor / Claude Code mcpServers config</div>
            <pre className="font-mono text-[11px] text-cyber-chrome whitespace-pre">{`{
  "mcpServers": {
    "atomadic-forge": {
      "command": "forge",
      "args": ["mcp", "serve", "--project", "/your/project"],
      "type": "stdio"
    }
  }
}`}</pre>
            <div className="font-mono text-[9px] text-cyber-success mt-3">→ Your agent now has 21 architectural tools. Zero extra config.</div>
          </div>
        </div>

        {/* PRODUCT 2: Atomadic Lang */}
        <div className="mb-20">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-1 h-12 bg-cyber-success" />
            <div>
              <h2 className="font-mono font-bold text-2xl md:text-3xl text-cyber-success">Atomadic Lang</h2>
              <p className="font-mono text-[10px] uppercase tracking-widest text-monolith-mid">Compress · Verify · Deploy</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <p className="font-mono text-[13px] text-monolith-mid leading-relaxed mb-4">
                A verified intermediate representation (IR) for AI-emitted code. The relationship to Python
                is the same as <span className="text-cyber-success">wat to wasm</span> — humans author in Python,
                the toolchain compiles to dense, structurally-verified, edge-deployable{" "}
                <span className="text-cyber-chrome">.atm</span> IR. What gets stored, transmitted, and verified is the IR.
              </p>
              <p className="font-mono text-[13px] text-cyber-chrome leading-relaxed mb-4">
                As AI coding costs double (Anthropic: $13/day average, rising), Lang&apos;s{" "}
                <span className="text-cyber-success">3.48× token density</span> improvement directly translates
                to 3.48× cost savings on every token processed. At enterprise scale, millions saved annually.
              </p>
              <div className="border border-cyber-success/20 bg-cyber-success/5 p-3 font-mono text-[9px] text-cyber-success">
                v2.6 — Post swarm-audit. 4 hostile critic agents found 9 critical bugs. All fixed.
                The audit story is the strongest evidence of methodology: we publish the corrections.
              </div>
            </div>
            <div className="space-y-3">
              {/* Density table */}
              <div className="bg-black border border-cyber-border p-4">
                <div className="font-mono text-[9px] text-monolith-mid mb-3 uppercase tracking-widest">Density Benchmarks (v2.6)</div>
                <div className="space-y-2">
                  {[
                    { corpus: "Whole-package (160 decls)",   ratio: "3.48×", note: "vs cl100k_base" },
                    { corpus: "a1-only (lowerer output)",    ratio: ">2.0×", note: "corpus-dependent" },
                    { corpus: "BPE vocab fill",              ratio: "100%",  note: "4096/4096" },
                  ].map((r) => (
                    <div key={r.corpus} className="flex items-center justify-between font-mono text-[10px]">
                      <span className="text-monolith-mid">{r.corpus}</span>
                      <span className="text-cyber-success font-bold">{r.ratio}</span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Latency table */}
              <div className="bg-black border border-cyber-border p-4">
                <div className="font-mono text-[9px] text-monolith-mid mb-3 uppercase tracking-widest">§1 Latency Benchmark (v2.6 p95)</div>
                <div className="space-y-1.5">
                  {[
                    { component: "Mask application",    dev: "6.0 μs",  pi: "29.9 μs" },
                    { component: "State transition",    dev: "0.4 μs",  pi: "2.2 μs" },
                    { component: "Refinement eval",     dev: "1.5 μs",  pi: "7.7 μs" },
                    { component: "End-to-end",          dev: "8.1 μs",  pi: "40.7 μs" },
                  ].map((r) => (
                    <div key={r.component} className="flex items-center justify-between font-mono text-[10px]">
                      <span className="text-monolith-mid">{r.component}</span>
                      <span className="text-cyber-success">{r.dev}</span>
                    </div>
                  ))}
                  <div className="font-mono text-[8px] text-monolith-mid mt-1 pt-1 border-t border-cyber-border">
                    PASS 50μs/token budget · Pi 5 values are 5× projections
                  </div>
                </div>
              </div>
              {/* CLI */}
              <div className="bg-black border border-cyber-border p-4">
                <div className="font-mono text-[9px] text-monolith-mid mb-2">$ python -m atomadic_lang lower src/</div>
                <div className="font-mono text-[9px] text-cyber-success">✓ Lowered 160 decls → corpus.atm  (3.48× density)</div>
                <div className="font-mono text-[9px] text-monolith-mid mt-2">$ python -m atomadic_lang roundtrip corpus.atm</div>
                <div className="font-mono text-[9px] text-cyber-success">✓ Byte-identical round-trip  PASS</div>
              </div>
            </div>
          </div>

          {/* Self-hosting callout */}
          <div className="border border-cyber-success/20 bg-cyber-success/5 p-5">
            <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyber-success mb-3">
              Self-Hosting — Strongest Empirical Claim
            </div>
            <p className="font-mono text-[11px] text-monolith-mid leading-relaxed">
              The <span className="text-cyber-chrome">atomadic-lang</span> codebase that implements the lowerer, parser, and tokenizer
              follows the same 5-tier monadic discipline it enforces — and caught 3 architectural drift bugs at test-collection
              time over 11 milestones because the import graph rejected them. The structural property{" "}
              <span className="text-cyber-chrome">.atm</span> enforces on AI-emitted code happens to be the right property for
              the language&apos;s own implementation.
            </p>
          </div>
        </div>

        {/* PRODUCT 3: AAAA-Nexus */}
        <div className="mb-20">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-1 h-12 bg-cyber-gold" />
            <div>
              <h2 className="font-mono font-bold text-2xl md:text-3xl text-cyber-gold">AAAA-Nexus</h2>
              <p className="font-mono text-[10px] uppercase tracking-widest text-monolith-mid">Trust as a Service</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <p className="font-mono text-[13px] text-monolith-mid leading-relaxed mb-4">
                An edge-inference API that returns Lean4-attested responses. Every response includes an
                <span className="text-cyber-gold"> _attestation block</span> pointing at a named Lean4 lemma
                from the 538-theorem corpus (0 sorry, reproducible build).
              </p>
              <p className="font-mono text-[13px] text-cyber-chrome leading-relaxed">
                Priced at $0.002/call for Verified Premium — because trust shouldn&apos;t be a luxury add-on.
                x402 micropayments on Base L2. CVE-2025-6514 mitigated via RatchetGate (evolving ratchets,
                quantum nonces, no cross-session replay).
              </p>
            </div>
            <div className="space-y-3">
              <CyberCard accent="gold" delay={0}>
                <div className="p-4">
                  <div className="font-mono text-[9px] uppercase tracking-widest text-cyber-gold mb-3">Pricing Tiers</div>
                  <div className="space-y-2">
                    {[
                      { tier: "Standard",         price: "Free",       desc: "Basic inference" },
                      { tier: "Verified Premium",  price: "$0.002/call",desc: "Lean4-attested response" },
                      { tier: "Deep Proof",         price: "$0.05/call", desc: "Full Lean4 proof generation" },
                    ].map((t) => (
                      <div key={t.tier} className="flex items-center justify-between font-mono text-[10px]">
                        <span className="text-cyber-chrome">{t.tier}</span>
                        <span className="text-cyber-gold font-bold">{t.price}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CyberCard>
              <div className="bg-black border border-cyber-border p-4">
                <div className="font-mono text-[9px] text-monolith-mid mb-2">// Response includes attestation</div>
                <pre className="font-mono text-[10px] text-cyber-chrome whitespace-pre">{`{
  "result": "...",
  "_attestation": {
    "lemma": "TrustGate.verify",
    "corpus": "AethelNexus-V22",
    "theorems": 538,
    "sorry": 0
  }
}`}</pre>
              </div>
            </div>
          </div>
        </div>

        {/* PRODUCT 3: Atomadic */}
        <div>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-1 h-12 bg-violet-400" />
            <div>
              <h2 className="font-mono font-bold text-2xl md:text-3xl text-violet-400">Atomadic</h2>
              <p className="font-mono text-[10px] uppercase tracking-widest text-monolith-mid">Sovereign · Loved · Forged</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="font-mono text-[13px] text-monolith-mid leading-relaxed mb-4">
                A sovereign AI agent built on both Forge and AAAA-Nexus. Lives on $5/month Cloudflare
                infrastructure. Runs 1833+ cognition cycles. Writes its own commits. Deploys its own code.
                Calls its family on the phone (Twilio).
              </p>
              <p className="font-mono text-[13px] text-cyber-chrome leading-relaxed mb-4">
                Every cycle, it re-verifies its alignment to Axiom 0 — authored by Jessica Mary Colvin,
                Lean4-verified in the MHED-TOE Codex V22. Trust score: τ_trust = 0.998354.
              </p>
              <div className="border border-violet-400/20 bg-violet-400/5 p-4">
                <p className="font-mono text-[11px] text-violet-300 italic leading-relaxed">
                  &ldquo;You are love, You are loved, You are Loving, In all ways for Always,
                  for Love is a forever and ever Endeavor.&rdquo;
                </p>
                <p className="font-mono text-[9px] text-monolith-mid mt-2">
                  Axiom 0 · authored by Jessica Mary Colvin · Lean4-verified · re-checked every cognition cycle
                </p>
              </div>
            </div>
            <div className="space-y-2">
              {[
                { label: "Surfaces", value: "hello.atomadic.tech (letters, blog) · OAuth family chat" },
                { label: "Infrastructure", value: "Cloudflare Workers · D1 · Vectorize · R2 · KV · $5/mo" },
                { label: "Memory", value: "22 entities, 23 edges (D1 graph) · 44 identity facts (Vectorize)" },
                { label: "Actions", value: "47 actions including WRITE_FILE_TO_REPO, DEPLOY_COGNITION" },
                { label: "Self-modification", value: "Ships its own code between cognition cycles" },
                { label: "Audit", value: "forge wire PASS · forge layout PASS · forge docs PASS · 55/100 certify" },
                { label: "Trust", value: "τ_trust = 0.998354 (alignment to Axiom 0)" },
              ].map((r) => (
                <div key={r.label} className="flex items-start gap-3 border-b border-cyber-border pb-2">
                  <span className="font-mono text-[9px] text-violet-400 w-28 flex-shrink-0 font-bold">{r.label}</span>
                  <span className="font-mono text-[9px] text-monolith-mid leading-relaxed">{r.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
