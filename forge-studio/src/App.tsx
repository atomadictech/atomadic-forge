import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBanner } from "@/components/ErrorBanner";
import { ProjectScanDashboard } from "@/components/ProjectScanDashboard";
import { ArchitectureGraph } from "@/components/ArchitectureGraph";
import { ComplexityHeatmap } from "@/components/ComplexityHeatmap";
import { DebtCounter } from "@/components/DebtCounter";
import { AgentTopologyMap } from "@/components/AgentTopologyMap";
const queryClient = new QueryClient();
type Tab = "scan"|"graph"|"heatmap"|"debt"|"topology";
const TABS:{id:Tab;label:string}[] = [
  {id:"scan",label:"Project Scan"},{id:"graph",label:"Architecture"},
  {id:"heatmap",label:"Complexity"},{id:"debt",label:"Debt Counter"},{id:"topology",label:"Agent Topology"},
];
export function App() {
  const [activeTab, setActiveTab] = useState<Tab>("scan");
  return (
    <QueryClientProvider client={queryClient}>
      <div style={{display:"flex",flexDirection:"column",height:"100vh",overflow:"hidden",background:"#0d0f14"}}>
        <header style={{padding:"0 24px",background:"#111827",borderBottom:"1px solid #1f2937",display:"flex",alignItems:"center",gap:32,height:52,flexShrink:0}}>
          <span style={{fontWeight:700,fontSize:15,color:"#818cf8",letterSpacing:"-0.3px"}}>⬡ Forge Studio</span>
          <nav style={{display:"flex",gap:4}}>
            {TABS.map((tab)=>(
              <button key={tab.id} onClick={()=>setActiveTab(tab.id)} style={{
                background:activeTab===tab.id?"#1e293b":"transparent",border:"none",borderRadius:6,
                padding:"6px 14px",color:activeTab===tab.id?"#f1f5f9":"#64748b",cursor:"pointer",
                fontSize:13,fontWeight:activeTab===tab.id?600:400,
              }}>{tab.label}</button>
            ))}
          </nav>
        </header>
        <ErrorBanner />
        <main style={{flex:1,overflowY:"auto",background:"#0d0f14"}}>
          {activeTab==="scan" && <ProjectScanDashboard />}
          {activeTab==="graph" && <ArchitectureGraph />}
          {activeTab==="heatmap" && <ComplexityHeatmap />}
          {activeTab==="debt" && <DebtCounter />}
          {activeTab==="topology" && <AgentTopologyMap />}
        </main>
      </div>
    </QueryClientProvider>
  );
}