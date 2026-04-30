import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../lib/forge-runner";

export async function POST(req: Request) {
  const { target } = (await req.json().catch(() => ({}))) as { target?: string };
  if (!target) {
    return NextResponse.json({ error: "target required" }, { status: 400 });
  }
  try {
    const report = await runForgeJson(["recon", target]);
    return NextResponse.json(report);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
