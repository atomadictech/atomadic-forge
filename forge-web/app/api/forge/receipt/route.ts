import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Reads the latest receipt from .atomadic-forge/receipt.json under the
 * given target. If absent, returns null.
 */
export async function POST(req: Request) {
  const { target } = (await req.json().catch(() => ({}))) as { target?: string };
  if (!target) {
    return NextResponse.json({ error: "target required" }, { status: 400 });
  }
  const receiptPath = path.join(target, ".atomadic-forge", "receipt.json");
  try {
    const data = await readFile(receiptPath, "utf-8");
    return NextResponse.json(JSON.parse(data));
  } catch {
    return NextResponse.json(null);
  }
}
