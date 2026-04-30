import { invoke } from "@tauri-apps/api/core";
import type { ScoutReport, WireReport, MctTool, McpResource } from "./types";
export async function connect(projectRoot:string):Promise<void> { await invoke<string>("forge_connect",{projectRoot}); }
export async function disconnect():Promise<void> { await invoke<void>("forge_disconnect"); }
export async function toolsList():Promise<MctTool[]> { const r=await invoke<{tools:MctTool[]}>("forge_tools_list"); return r.tools??[]; }
export async function resourcesList():Promise<McpResource[]> { const r=await invoke<{resources:McpResource[]}>("forge_resources_list"); return r.resources??[]; }
export async function callRecon(target:string):Promise<ScoutReport> { return invoke<ScoutReport>("forge_call_tool",{name:"recon",arguments:{target}}); }
export async function callWire(source:string,suggestRepairs=false):Promise<WireReport> { return invoke<WireReport>("forge_call_tool",{name:"wire",arguments:{source,suggest_repairs:suggestRepairs}}); }
export async function callEnforce(source:string,apply=false):Promise<unknown> { return invoke("forge_call_tool",{name:"enforce",arguments:{source,apply}}); }