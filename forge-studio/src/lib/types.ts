export type Tier = "a0"|"a1"|"a2"|"a3"|"a4";
export interface TierDistribution { a0:number;a1:number;a2:number;a3:number;a4:number;unknown:number; }
export interface ScoutSymbol { name:string;kind:string;tier:Tier|"unknown";file:string;line:number;loc?:number; }
export interface ScoutReport { schema_version:string;project_root:string;tier_distribution:TierDistribution;symbols:ScoutSymbol[];file_count:number;symbol_count:number;scanned_at?:string; }
export type ViolationSeverity = "error"|"warn"|"info";
export interface WireViolation { file:string;line:number;severity:ViolationSeverity;message:string;autofixable?:boolean;repair_suggestion?:string; }
export interface WireReport { schema_version:string;source:string;violations:WireViolation[];violation_count:number;autofixable_count:number;files_scanned:number; }
export interface MctTool { name:string;description:string;inputSchema:Record<string,unknown>; }
export interface McpResource { uri:string;name:string;description?:string;mimeType?:string; }
export type ConnectionStatus = "disconnected"|"connecting"|"connected"|"error";
export interface DebtConfig { hourlyRate:number; }
export const SEVERITY_WEIGHTS:Record<ViolationSeverity,number> = { error:4, warn:2, info:1 };