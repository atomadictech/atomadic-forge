import { useForgeStore } from "@/store";
import * as mcp from "@/lib/mcp";
export function ErrorBanner() {
  const { error, projectRoot, setError, setStatus, setTools, setResources, setScoutReport, setWireReport } = useForgeStore();
  if (!error) return null;
  async function handleReconnect() {
    if (!projectRoot) return;
    setError(null);
    setStatus("connecting");
    try {
      await mcp.connect(projectRoot);
      setStatus("connected");
      const [tools, resources, scout, wire] = await Promise.all([
        mcp.toolsList(), mcp.resourcesList(),
        mcp.callRecon(projectRoot), mcp.callWire(projectRoot, true),
      ]);
      setTools(tools); setResources(resources); setScoutReport(scout); setWireReport(wire);
    } catch (e) { setError(String(e)); setStatus("error"); }
  }
  return (
    <div role="alert" style={{background:"#7f1d1d",color:"#fecaca",padding:"8px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",fontSize:13,borderBottom:"1px solid #991b1b"}}>
      <span>⚠ {error}</span>
      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        {projectRoot && (
          <button onClick={handleReconnect}
            style={{background:"#991b1b",border:"1px solid #ef4444",color:"#fecaca",cursor:"pointer",fontSize:12,borderRadius:4,padding:"2px 10px"}}>
            Reconnect
          </button>
        )}
        <button onClick={()=>setError(null)} style={{background:"none",border:"none",color:"#fecaca",cursor:"pointer",fontSize:16}} aria-label="dismiss error">×</button>
      </div>
    </div>
  );
}
