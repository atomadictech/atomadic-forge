import { useState } from "react";
import { useForgeStore } from "@/store";
import * as mcp from "@/lib/mcp";
import type { Tier } from "@/lib/types";
const TC:Record<Tier|"unknown",string>={a0:"#818cf8",a1:"#34d399",a2:"#60a5fa",a3:"#f472b6",a4:"#fb923c",unknown:"#6b7280"};
const TL:Record<Tier|"unknown",string>={a0:"a0 · Constants",a1:"a1 · Functions",a2:"a2 · Composites",a3:"a3 · Features",a4:"a4 · Orchestration",unknown:"Unknown"};
export function ProjectScanDashboard() {
  const {status,projectRoot,scoutReport,wireReport,selectedTier,setProjectRoot,setStatus,setError,setScoutReport,setWireReport,setTools,setResources,setSelectedTier}=useForgeStore();
  const [inputPath,setInputPath]=useState(projectRoot??"");
  const [scanning,setScanning]=useState(false);
  async function handleScan(){
    const root=inputPath.trim(); if(!root)return;
    setScanning(true);setError(null);
    try{setStatus("connecting");await mcp.connect(root);setProjectRoot(root);setStatus("connected");
      const[tools,resources,scout,wire]=await Promise.all([mcp.toolsList(),mcp.resourcesList(),mcp.callRecon(root),mcp.callWire(root,true)]);
      setTools(tools);setResources(resources);setScoutReport(scout);setWireReport(wire);
    }catch(e){setError(String(e));setStatus("error");}finally{setScanning(false);}
  }
  const dist=scoutReport?.tier_distribution;
  const tiers:(Tier|"unknown")[]=["a0","a1","a2","a3","a4","unknown"];
  const total=dist?Object.values(dist).reduce((s,n)=>s+n,0):0;
  const tierFiles=selectedTier&&scoutReport?scoutReport.symbols.filter((s)=>s.tier===selectedTier):[];
  return(
    <section style={{padding:24}}>
      <h2 style={{fontSize:18,fontWeight:600,marginBottom:16,color:"#f1f5f9"}}>Project Scan</h2>
      <div data-testid="drop-zone" onDragOver={(e)=>e.preventDefault()} onDrop={(e)=>{e.preventDefault();setInputPath(e.dataTransfer.getData("text/plain")||inputPath);}}
        style={{border:"2px dashed #334155",borderRadius:8,padding:24,marginBottom:20,display:"flex",gap:12,alignItems:"center",background:"#1e293b"}}>
        <input type="text" value={inputPath} onChange={(e)=>setInputPath(e.target.value)} placeholder="Drop a folder or paste a path…" onKeyDown={(e)=>e.key==="Enter"&&handleScan()}
          style={{flex:1,background:"#0f172a",border:"1px solid #334155",borderRadius:6,padding:"8px 12px",color:"#e2e8f0",fontSize:14,outline:"none"}} aria-label="project path"/>
        <button onClick={handleScan} disabled={scanning||!inputPath.trim()}
          style={{background:scanning?"#334155":"#4f46e5",color:"#fff",border:"none",borderRadius:6,padding:"8px 20px",cursor:scanning?"default":"pointer",fontSize:14,fontWeight:600}}>
          {scanning?"Scanning…":"Scan"}</button>
      </div>
      {status!=="disconnected"&&(<div style={{marginBottom:16,fontSize:13}}>
        <span style={{background:status==="connected"?"#064e3b":status==="error"?"#7f1d1d":"#1e3a5f",color:status==="connected"?"#6ee7b7":status==="error"?"#fca5a5":"#93c5fd",borderRadius:4,padding:"2px 8px"}}>{status}</span>
        {projectRoot&&<span style={{marginLeft:8,color:"#64748b"}}>{projectRoot}</span>}
      </div>)}
      {scoutReport&&dist&&(<>
        <div style={{display:"flex",gap:16,marginBottom:20,flexWrap:"wrap"}}>
          {([["Files",scoutReport.file_count],["Symbols",scoutReport.symbol_count],["Violations",wireReport?.violation_count??"—"],["Auto-fixable",wireReport?.autofixable_count??"—"]] as [string,number|string][]).map(([label,value])=>(
            <div key={label} style={{background:"#1e293b",border:"1px solid #334155",borderRadius:8,padding:"12px 20px",minWidth:100}}>
              <div style={{fontSize:22,fontWeight:700,color:"#f1f5f9"}}>{value}</div>
              <div style={{fontSize:12,color:"#64748b",marginTop:2}}>{label}</div>
            </div>
          ))}
        </div>
        <div style={{marginBottom:20}}>
          <div style={{fontSize:13,color:"#94a3b8",marginBottom:8}}>Tier Distribution</div>
          {tiers.map((tier)=>{const count=dist[tier as keyof typeof dist]??0;const pct=total>0?(count/total)*100:0;return(
            <div key={tier} style={{display:"flex",alignItems:"center",gap:10,marginBottom:6,cursor:"pointer",opacity:selectedTier&&selectedTier!==tier?0.5:1}}
              onClick={()=>setSelectedTier(selectedTier===tier?null:(tier as Tier))} role="button" aria-label={`tier ${tier}: ${count} symbols`}>
              <span style={{width:100,fontSize:12,color:TC[tier],flexShrink:0}}>{TL[tier]}</span>
              <div style={{flex:1,background:"#1e293b",borderRadius:4,height:14,overflow:"hidden"}}>
                <div data-testid={`tier-bar-${tier}`} style={{width:`${pct}%`,height:"100%",background:TC[tier],borderRadius:4,transition:"width 0.4s ease"}}/>
              </div>
              <span style={{width:32,fontSize:12,color:"#64748b",textAlign:"right"}}>{count}</span>
            </div>
          );})}
        </div>
        {selectedTier&&(<div>
          <div style={{fontSize:13,color:"#94a3b8",marginBottom:8}}>{TL[selectedTier]} — {tierFiles.length} symbols</div>
          <div style={{background:"#0f172a",borderRadius:6,border:"1px solid #1e293b",maxHeight:240,overflowY:"auto",fontSize:12,fontFamily:"monospace"}}>
            {tierFiles.slice(0,200).map((sym,i)=>(
              <div key={i} style={{padding:"4px 12px",borderBottom:"1px solid #1e293b",display:"flex",gap:12,color:"#cbd5e1"}}>
                <span style={{color:"#64748b",minWidth:60}}>{sym.kind}</span>
                <span style={{color:"#e2e8f0"}}>{sym.name}</span>
                <span style={{color:"#475569",marginLeft:"auto"}}>{sym.file}:{sym.line}</span>
              </div>
            ))}
          </div>
        </div>)}
      </>)}
    </section>
  );
}