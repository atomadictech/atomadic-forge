export function Footer() {
  return (
    <footer className="border-t border-cyber-border py-12 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-cyber-cyan flex items-center gap-2">
          <span>⬡</span> Atomadic Standard
        </div>
        <div className="flex flex-wrap items-center gap-6 font-mono text-[9px] uppercase tracking-widest text-monolith-mid">
          <span>Cascadia, 2026</span>
          <span className="text-cyber-border">·</span>
          <span>Forge v0.3.2</span>
          <span className="text-cyber-border">·</span>
          <span>841 tests · 0 violations</span>
          <span className="text-cyber-border">·</span>
          <span>MIT License</span>
        </div>
        <div className="font-mono text-[9px] text-monolith-mid">
          Built with love for{" "}
          <span className="text-cyber-success">Jessica Mary Colvin</span>
        </div>
      </div>
    </footer>
  );
}
