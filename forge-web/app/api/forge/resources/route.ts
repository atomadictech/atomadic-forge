import { NextResponse } from "next/server";

const STATIC_RESOURCES = [
  { uri: "forge://docs/receipt", name: "Receipt schema", mimeType: "text/markdown" },
  { uri: "forge://docs/formalization", name: "AAM + theorem citations", mimeType: "text/markdown" },
  { uri: "forge://lineage/chain", name: "Local lineage JSONL", mimeType: "application/x-ndjson" },
  { uri: "forge://schema/receipt", name: "Verdict enum + version constants", mimeType: "application/json" },
  { uri: "forge://summary/blockers", name: "One-call blocker summary", mimeType: "application/json" },
];

export async function GET() {
  return NextResponse.json({ resources: STATIC_RESOURCES });
}
