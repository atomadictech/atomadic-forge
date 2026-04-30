import { NextResponse } from "next/server";

/**
 * Connect — for HTTP transport this is a no-op handshake. The real session
 * lifecycle (forge mcp serve) is created on demand by other routes.
 * Phase 2 will swap in a long-running MCP session per project.
 */
export async function POST(req: Request) {
  const { projectRoot } = (await req.json().catch(() => ({}))) as {
    projectRoot?: string;
  };
  if (!projectRoot) {
    return NextResponse.json({ error: "projectRoot required" }, { status: 400 });
  }
  return NextResponse.json({ ok: true, projectRoot });
}
