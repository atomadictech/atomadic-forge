import { useForgeStore } from "../store";
import { useForgeClient } from "../client/context";

export function ErrorBanner() {
  const {
    error,
    projectRoot,
    setError,
    setStatus,
    setTools,
    setResources,
    setScoutReport,
    setWireReport,
  } = useForgeStore();
  const client = useForgeClient();
  if (!error) return null;

  async function handleReconnect() {
    if (!projectRoot) return;
    setError(null);
    setStatus("connecting");
    try {
      await client.connect(projectRoot);
      setStatus("connected");
      const [tools, resources, scout, wire] = await Promise.all([
        client.toolsList(),
        client.resourcesList(),
        client.recon(projectRoot),
        client.wire(projectRoot, true),
      ]);
      setTools(tools);
      setResources(resources);
      setScoutReport(scout);
      setWireReport(wire);
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  }

  return (
    <div
      role="alert"
      className="flex items-center justify-between px-4 py-2 bg-cyber-alert/10 border-b border-cyber-alert/30 font-mono text-[11px]"
    >
      <span className="text-cyber-alert flex items-center gap-2">
        <span className="text-[8px]">▲</span>
        {error}
      </span>
      <div className="flex items-center gap-2">
        {projectRoot && (
          <button
            onClick={handleReconnect}
            className="border border-cyber-alert/50 text-cyber-alert px-3 py-0.5 text-[10px] uppercase tracking-widest hover:bg-cyber-alert hover:text-white transition-colors"
          >
            Reconnect
          </button>
        )}
        <button
          onClick={() => setError(null)}
          className="text-cyber-alert/70 hover:text-cyber-alert transition-colors px-1 text-base leading-none"
          aria-label="dismiss error"
        >
          ×
        </button>
      </div>
    </div>
  );
}
