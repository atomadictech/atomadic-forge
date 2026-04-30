"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Menu, X } from "lucide-react";

const LINKS = [
  { href: "#problem", label: "Problem" },
  { href: "#solution", label: "Solution" },
  { href: "#products", label: "Products" },
  { href: "#ecosystem", label: "Ecosystem" },
  { href: "#receipts", label: "Receipts" },
  { href: "#market", label: "Market" },
  { href: "#traction", label: "Traction" },
  { href: "#team", label: "Team" },
  { href: "#invest", label: "Invest" },
];

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-black/90 backdrop-blur-md border-b border-cyber-border" : "bg-transparent"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <a
          href="#"
          className="font-mono text-[11px] uppercase tracking-[0.4em] text-cyber-cyan flex items-center gap-2"
        >
          <span className="text-base">⬡</span> Atomadic
        </a>

        {/* Desktop links */}
        <div className="hidden lg:flex items-center gap-5">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="font-mono text-[9px] uppercase tracking-[0.25em] text-monolith-mid hover:text-cyber-cyan transition-colors"
            >
              {l.label}
            </a>
          ))}
          <a
            href="#invest"
            className="ml-2 border border-cyber-cyan text-cyber-cyan font-mono text-[9px] uppercase tracking-[0.25em] px-4 py-1.5 hover:bg-cyber-cyan hover:text-black transition-colors"
          >
            Talk to us
          </a>
        </div>

        {/* Mobile toggle */}
        <button
          className="lg:hidden text-cyber-cyan"
          onClick={() => setOpen(!open)}
          aria-label="toggle menu"
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden bg-black border-b border-cyber-border overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col gap-4">
              {LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="font-mono text-[10px] uppercase tracking-widest text-monolith-mid hover:text-cyber-cyan transition-colors"
                >
                  {l.label}
                </a>
              ))}
              <a
                href="#invest"
                onClick={() => setOpen(false)}
                className="self-start border border-cyber-cyan text-cyber-cyan font-mono text-[10px] uppercase tracking-widest px-4 py-2 hover:bg-cyber-cyan hover:text-black transition-colors"
              >
                Talk to us
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
