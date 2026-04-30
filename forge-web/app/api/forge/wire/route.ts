import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../lib/forge-runner";

export async function POST(req: Request) {
  const { source, suggest_repairs } = (await req.json().catch(() => ({}))) as {
    source?: string;
    suggest_repairs?: boolean;
  };
  if (!source) {
    return NextResponse.json({ error: "source required" }, { status: 400 });
  }
  const args = ["wire", source];
  if (suggest_repairs) args.push("--suggest-repairs");
  try {
    const report = await runForgeJson(args);
    return NextResponse.json(report);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
