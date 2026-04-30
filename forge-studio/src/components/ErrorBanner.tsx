import { useForgeStore } from "@/store";
export function ErrorBanner() {
  const { error, setError } = useForgeStore();
  if (!error) return null;
  return (
    <div role="alert" style={{background:"#7f1d1d",color:"#fecaca",padding:"8px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",fontSize:13,borderBottom:"1px solid #991b1b"}}>
      <span>⚠ {error}</span>
      <button onClick={()=>setError(null)} style={{background:"none",border:"none",color:"#fecaca",cursor:"pointer",fontSize:16}} aria-label="dismiss error">×</button>
    </div>
  );
}