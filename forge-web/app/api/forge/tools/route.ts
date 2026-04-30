import { NextResponse } from "next/server";

/**
 * Phase 1: return a static manifest of forge MCP tools.
 * Phase 2 will replace with a live `forge mcp serve` session that calls tools/list.
 */
const STATIC_TOOLS = [
  { name: "recon", description: "Scout symbols and classify into 5-tier monadic layout", inputSchema: {} },
  { name: "wire", description: "Validate tier imports and surface F-code violations", inputSchema: {} },
  { name: "certify", description: "Score conformance (documentation, tests, tier layout, imports)", inputSchema: {} },
  { name: "enforce", description: "Auto-generate and apply mechanical fixes for wire violations", inputSchema: {} },
  { name: "auto_plan", description: "Generate ranked agent action cards", inputSchema: {} },
  { name: "context_pack", description: "One-call repo orientation for agents", inputSchema: {} },
  { name: "preflight_change", description: "Pre-edit guardrail — detect tier, forbidden imports, scope", inputSchema: {} },
  { name: "list_recipes", description: "List Forge release/repair recipes", inputSchema: {} },
];

export async function GET() {
  return NextResponse.json({ tools: STATIC_TOOLS });
}
