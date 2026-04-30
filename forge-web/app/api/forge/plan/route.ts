import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../lib/forge-runner";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    target?: string;
    goal?: string;
    mode?: "improve" | "absorb";
    top?: number;
    save?: boolean;
  };
  if (!body.target) {
    return NextResponse.json({ error: "target required" }, { status: 400 });
  }
  const args = ["plan", body.target];
  if (body.goal) args.push("--goal", body.goal);
  if (body.mode) args.push("--mode", body.mode);
  if (body.top !== undefined) args.push("--top", String(body.top));
  if (body.save) args.push("--save");
  try {
    const plan = await runForgeJson(args);
    return NextResponse.json(plan);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
