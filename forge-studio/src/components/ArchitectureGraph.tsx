import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import { useForgeStore } from "@/store";
import type { Tier } from "@/lib/types";
const TC:Record<Tier,string>={a0:"#818cf8",a1:"#34d399",a2:"#60a5fa",a3:"#f472b6",a4:"#fb923c"};
const TL:Record<Tier,string>={a0:"a0\nConstants",a1:"a1\nFunctions",a2:"a2\nComposites",a3:"a3\nFeatures",a4:"a4\nOrchestration"};
const EDGES:[Tier,Tier][]=[ ["a1","a0"],["a2","a0"],["a2","a1"],["a3","a0"],["a3","a1"],["a3","a2"],["a4","a0"],["a4","a1"],["a4","a2"],["a4","a3"] ];
export function ArchitectureGraph() {
  const cyRef=useRef<HTMLDivElement>(null);
  const cyInstance=useRef<Core|null>(null);
  const {scoutReport,selectedTier,setSelectedTier}=useForgeStore();
  useEffect(()=>{
    if(!cyRef.current)return;
    const tiers:Tier[]=["a0","a1","a2","a3","a4"];
    const counts=scoutReport?Object.fromEntries(tiers.map((t)=>[t,scoutReport.symbols.filter((s)=>s.tier===t).length])):Object.fromEntries(tiers.map((t)=>[t,0]));
    const nodes=tiers.map((tier,i)=>({data:{id:tier,label:TL[tier],count:counts[tier]??0,color:TC[tier]},position:{x:80+i*110,y:420-i*90}}));
    const edges=EDGES.map(([from,to])=>({data:{id:`${from}-${to}`,source:from,target:to}}));
    cyInstance.current?.destroy();
    const cy=cytoscape({container:cyRef.current,elements:{nodes,edges},
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      style:([
        {selector:"node",style:{"shape":"round-rectangle",width:120,height:56,"background-color":"data(color)","background-opacity":0.15,"border-color":"data(color)","border-width":2,label:"data(label)","text-valign":"center","text-halign":"center",color:"#e2e8f0","font-size":11,"white-space":"pre","text-wrap":"wrap"} as Record<string,unknown>},
        {selector:"node:selected",style:{"background-opacity":0.4,"border-width":3}},
        {selector:"edge",style:{width:1.5,"line-color":"#334155","target-arrow-color":"#475569","target-arrow-shape":"triangle","curve-style":"bezier",opacity:0.6}},
      ] as any),
      layout:{name:"preset"},userZoomingEnabled:true,userPanningEnabled:true,
    });
    cy.on("tap","node",(evt)=>{const tier=evt.target.id() as Tier;setSelectedTier(selectedTier===tier?null:tier);});
    cyInstance.current=cy;
    return ()=>{cy.destroy();cyInstance.current=null;};
  },[scoutReport]);
  useEffect(()=>{
    const cy=cyInstance.current;if(!cy)return;
    cy.nodes().forEach((node)=>{const sel=node.id()===selectedTier;node.style("background-opacity",sel?0.45:0.15);node.style("border-width",sel?3:2);});
  },[selectedTier]);
  return(
    <section style={{padding:24}}>
      <h2 style={{fontSize:18,fontWeight:600,marginBottom:8,color:"#f1f5f9"}}>Architecture Graph</h2>
      <p style={{fontSize:12,color:"#64748b",marginBottom:16}}>5-tier monadic law — edges show allowed upward-only imports. Click a node to filter symbols.</p>
      {scoutReport?(
        <div ref={cyRef} data-testid="arch-graph" style={{width:"100%",height:560,background:"#0f172a",borderRadius:8,border:"1px solid #1e293b"}}/>
      ):(
        <div style={{height:200,display:"flex",alignItems:"center",justifyContent:"center",color:"#475569",fontSize:14,border:"1px dashed #334155",borderRadius:8}}>
          Scan a project to render the architecture graph
        </div>
      )}
    </section>
  );
}