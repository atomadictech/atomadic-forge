import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../../../lib/forge-runner";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { cardId, apply } = (await req.json().catch(() => ({}))) as {
    cardId?: string;
    apply?: boolean;
  };
  if (!cardId) {
    return NextResponse.json({ error: "cardId required" }, { status: 400 });
  }
  const args = ["plan-step", id, cardId];
  if (apply) args.push("--apply");
  try {
    const out = await runForgeJson(args);
    return NextResponse.json(out);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
