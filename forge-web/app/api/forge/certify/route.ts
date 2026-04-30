import { NextResponse } from "next/server";
import { runForgeJson } from "../../../../lib/forge-runner";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    source?: string;
    emitReceipt?: boolean;
    receiptPath?: string;
    sign?: boolean;
    localSign?: boolean;
    failUnder?: number;
  };
  if (!body.source) {
    return NextResponse.json({ error: "source required" }, { status: 400 });
  }
  const args = ["certify", body.source];
  if (body.emitReceipt) args.push("--emit-receipt");
  if (body.receiptPath) args.push("--out", body.receiptPath);
  if (body.localSign) args.push("--local-sign");
  if (body.sign) args.push("--sign");
  if (body.failUnder !== undefined) args.push("--fail-under", String(body.failUnder));
  try {
    const result = await runForgeJson(args, { timeoutMs: 120_000 });
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
