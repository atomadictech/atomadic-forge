import { useForgeStore } from "../store";

export function SettingsPanel() {
  const { debtConfig, setDebtConfig } = useForgeStore();
  return (
    <div className="p-8 max-w-lg">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.3em] text-monolith-muted mb-8">
        Configuration
      </h2>
      <div className="border border-cyber-border bg-cyber-panel p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-cyber-chrome">
              Hourly Rate
            </div>
            <div className="text-[9px] text-monolith-muted mt-1">
              Used by the CISQ debt counter
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-monolith-muted font-mono text-xs">$</span>
            <input
              type="number"
              min={1}
              max={999}
              value={debtConfig.hourlyRate}
              onChange={(e) =>
                setDebtConfig({ hourlyRate: Number(e.target.value) || 80 })
              }
              className="w-20 bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-sm px-2 py-1 focus:outline-none focus:border-cyber-cyan"
            />
            <span className="text-monolith-muted font-mono text-xs">/hr</span>
          </div>
        </div>
        <div className="border-t border-cyber-border pt-4 text-[9px] text-monolith-muted font-mono space-y-1">
          <div>F004x structural violations · weight 4</div>
          <div>F003x effect violations · weight 2</div>
          <div>other F-codes · weight 1</div>
        </div>
      </div>
    </div>
  );
}
