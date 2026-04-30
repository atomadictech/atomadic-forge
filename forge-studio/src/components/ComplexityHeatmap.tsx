import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useForgeStore } from "@/store";
interface FC{file:string;score:number;}
function stc(s:number):string{const r=s<50?Math.round((s/50)*250):250;const g=s<50?200:Math.round(200-((s-50)/50)*150);return `rgb(${r},${g},60)`;}
async function fetchComplexity(files:string[]):Promise<FC[]>{
  const results:FC[]=[];
  for(const file of files.slice(0,100)){try{const s=await invoke<number>("complexipy_score",{file});results.push({file,score:Math.min(100,Math.max(0,s))});}catch{throw new Error("complexipy unavailable");}}
  return results;
}
export function ComplexityHeatmap(){
  const{scoutReport}=useForgeStore();
  const[complexities,setComplexities]=useState<FC[]|null>(null);
  const[unavailable,setUnavailable]=useState(false);
  useEffect(()=>{
    if(!scoutReport)return;
    const files=[...new Set(scoutReport.symbols.map((s)=>s.file))].filter((f)=>f.endsWith(".py"));
    if(files.length===0)return;
    fetchComplexity(files).then(setComplexities).catch(()=>setUnavailable(true));
  },[scoutReport]);
  if(!scoutReport)return null;
  if(unavailable)return(
    <section style={{padding:24}}>
      <h2 style={{fontSize:18,fontWeight:600,marginBottom:8,color:"#f1f5f9"}}>Complexity Heatmap</h2>
      <div style={{background:"#1e293b",border:"1px dashed #475569",borderRadius:8,padding:20,color:"#64748b",fontSize:13}}>
        <strong style={{color:"#94a3b8"}}>complexipy not installed</strong><br/>Install for cognitive complexity overlay:
        <code style={{display:"block",marginTop:8,background:"#0f172a",padding:"6px 10px",borderRadius:4,fontFamily:"monospace",color:"#7dd3fc"}}>pip install complexipy</code>
      </div>
    </section>
  );
  if(!complexities)return null;
  const sorted=[...complexities].sort((a,b)=>b.score-a.score);
  return(
    <section style={{padding:24}}>
      <h2 style={{fontSize:18,fontWeight:600,marginBottom:8,color:"#f1f5f9"}}>Complexity Heatmap</h2>
      <p style={{fontSize:12,color:"#64748b",marginBottom:16}}>Cognitive complexity score per file (0=trivial→100=critical).</p>
      <div data-testid="complexity-heatmap" style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))",gap:8}}>
        {sorted.map(({file,score})=>{const short=file.split(/[\\/]/).slice(-2).join("/");return(
          <div key={file} title={`${file} — score ${score}`} style={{background:stc(score),borderRadius:6,padding:"8px 10px",fontSize:11,fontFamily:"monospace",color:score>60?"#fff":"#0f172a",opacity:0.92}}>
            <div style={{fontWeight:600}}>{score}</div>
            <div style={{opacity:0.85,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{short}</div>
          </div>
        );})}
      </div>
    </section>
  );
}