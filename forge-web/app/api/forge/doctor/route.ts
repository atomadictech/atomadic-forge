import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../lib/forge-runner";

export async function GET() {
  try {
    const r = await runForgeJson(["doctor"]);
    return NextResponse.json(r);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
