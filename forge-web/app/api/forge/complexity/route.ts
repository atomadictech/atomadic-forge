import { NextResponse } from "next/server";
import { runForge } from "../../../../lib/forge-runner";

/**
 * Forwards to `complexipy <file> --json` if available on the host.
 * Returns { score: 0-100 } or 503 if complexipy is not installed.
 */
export async function POST(req: Request) {
  const { file } = (await req.json().catch(() => ({}))) as { file?: string };
  if (!file) {
    return NextResponse.json({ error: "file required" }, { status: 400 });
  }
  // complexipy is not part of the forge CLI — call directly
  const r = await new Promise<{ ok: boolean; stdout: string; stderr: string }>(
    (resolve) => {
      runForge([], {}); // typing only
      // minimal subprocess invoke for the complexipy binary
      const { spawn } = require("node:child_process") as typeof import("node:child_process");
      const child = spawn("complexipy", [file, "--quiet", "--output-json"]);
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
      child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
      child.on("error", (err: Error) =>
        resolve({ ok: false, stdout, stderr: stderr + String(err) }),
      );
      child.on("close", (code: number) =>
        resolve({ ok: code === 0, stdout, stderr }),
      );
    },
  );
  if (!r.ok) {
    return NextResponse.json(
      { error: r.stderr || "complexipy unavailable" },
      { status: 503 },
    );
  }
  try {
    const parsed = JSON.parse(r.stdout) as { complexity?: number; score?: number };
    const score = parsed.score ?? parsed.complexity ?? 0;
    return NextResponse.json({ score });
  } catch {
    return NextResponse.json({ score: 0 });
  }
}
