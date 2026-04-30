import { create } from "zustand";
import type { ConnectionStatus,DebtConfig,ScoutReport,WireReport,MctTool,McpResource,Tier } from "@/lib/types";
interface ForgeState {
  status:ConnectionStatus;projectRoot:string|null;error:string|null;
  scoutReport:ScoutReport|null;wireReport:WireReport|null;tools:MctTool[];resources:McpResource[];
  selectedTier:Tier|null;debtConfig:DebtConfig;
  setStatus:(s:ConnectionStatus)=>void;setProjectRoot:(p:string)=>void;setError:(e:string|null)=>void;
  setScoutReport:(r:ScoutReport)=>void;setWireReport:(r:WireReport)=>void;
  setTools:(t:MctTool[])=>void;setResources:(r:McpResource[])=>void;
  setSelectedTier:(t:Tier|null)=>void;setDebtConfig:(c:Partial<DebtConfig>)=>void;reset:()=>void;
}
export const useForgeStore = create<ForgeState>((set) => ({
  status:"disconnected",projectRoot:null,error:null,scoutReport:null,wireReport:null,
  tools:[],resources:[],selectedTier:null,debtConfig:{hourlyRate:80},
  setStatus:(s)=>set({status:s}),setProjectRoot:(p)=>set({projectRoot:p}),
  setError:(e)=>set({error:e}),setScoutReport:(r)=>set({scoutReport:r}),
  setWireReport:(r)=>set({wireReport:r}),setTools:(t)=>set({tools:t}),
  setResources:(r)=>set({resources:r}),setSelectedTier:(t)=>set({selectedTier:t}),
  setDebtConfig:(c)=>set((s)=>({debtConfig:{...s.debtConfig,...c}})),
  reset:()=>set({status:"disconnected",projectRoot:null,error:null,scoutReport:null,wireReport:null,tools:[],resources:[],selectedTier:null}),
}));