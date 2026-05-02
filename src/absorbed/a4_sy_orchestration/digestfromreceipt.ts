// Atomadic Forge — badge Cloudflare Worker
//
// Golden Path Lane C W3. Returns a shields.io-compatible SVG badge
// summarising the latest Forge Receipt for `<owner>/<repo>` (and
// optionally a branch).
//
// URL shape:
//   GET /badge/<owner>/<repo>.svg                  -> default branch
//   GET /badge/<owner>/<repo>/<branch>.svg
//   GET /badge/<owner>/<repo>.json                 -> raw shields.io
//                                                     dynamic-badge JSON
//
// Storage:
//   KV namespace FORGE_RECEIPTS, key 'receipt:<owner>:<repo>:<branch>',
//   value = serialized atomadic-forge.receipt/v1 JSON.
//
// The github-action ('atomadictech/atomadic-forge/.github/actions/
// forge-action' — Lane C W1) PUTs to this KV after every passing CI
// run. Until that path is wired, the worker returns a clear "no
// receipt yet — install the action" badge instead of erroring.

export interface Env {
  FORGE_RECEIPTS: KVNamespace;
  DEFAULT_BRANCH?: string;
}

interface ReceiptDigest {
  schema_version: string;
  verdict: string;
  certify_score: number | null;
  generated_at_utc: string;
  forge_version: string;
  wire_verdict: string | null;
}

const SHIELD_GREEN = "#4c1"; // forge_certify ≥ 75 PASS
const SHIELD_YELLOWGREEN = "#a4a61d";
const SHIELD_YELLOW = "#dfb317";
const SHIELD_ORANGE = "#fe7d37";
const SHIELD_RED = "#e05d44";
const SHIELD_GREY = "#9f9f9f";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const m = url.pathname.match(
      /^\/badge\/([^/]+)\/([^/.]+)(?:\/([^/.]+))?\.(svg|json)$/,
    );
    if (!m) {
      return new Response(notFoundSvg(), {
        status: 404,
        headers: svgHeaders(),
      });
    }
    const owner = decodeURIComponent(m[1]);
    const repo = decodeURIComponent(m[2]);
    const branch = decodeURIComponent(m[3] ?? env.DEFAULT_BRANCH ?? "main");
    const fmt = m[4];

    const digest = await loadReceiptDigest(env, owner, repo, branch);

    if (fmt === "json") {
      return new Response(JSON.stringify(badgeJson(digest)), {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "public, max-age=300",
          ...corsHeaders(),
        },
      });
    }
    return new Response(renderSvg(digest), {
      headers: svgHeaders(),
    });
  },
};

async function loadReceiptDigest(
  env: Env,
  owner: string,
  repo: string,
  branch: string,
): Promise<ReceiptDigest | null> {
  const key = `receipt:${owner}:${repo}:${branch}`;
  const raw = await env.FORGE_RECEIPTS.get(key);
  if (!raw) return null;
  try {
    const receipt = JSON.parse(raw);
    return digestFromReceipt(receipt);
  } catch {
    return null;
  }
}

export function digestFromReceipt(receipt: any): ReceiptDigest | null {
  if (!receipt || typeof receipt !== "object") return null;
  if (typeof receipt.schema_version !== "string") return null;
  if (!receipt.schema_version.startsWith("atomadic-forge.receipt/")) return null;
  return {
    schema_version: receipt.schema_version,
    verdict: typeof receipt.verdict === "string" ? receipt.verdict : "?",
    certify_score:
      typeof receipt?.certify?.score === "number" ? receipt.certify.score : null,
    generated_at_utc: receipt.generated_at_utc ?? "",
    forge_version: receipt.forge_version ?? "",
    wire_verdict: receipt?.wire?.verdict ?? null,
  };
}

export function badgeColorFor(score: number | null, verdict: string): string {
  if (verdict === "PASS" && score !== null && score >= 100) return SHIELD_GREEN;
  if (verdict === "PASS" && score !== null && score >= 90) return SHIELD_YELLOWGREEN;
  if (score !== null && score >= 75) return SHIELD_YELLOW;
  if (score !== null && score >= 50) return SHIELD_ORANGE;
  if (score !== null) return SHIELD_RED;
  return SHIELD_GREY;
}

export function badgeMessageFor(digest: ReceiptDigest | null): string {
  if (!digest) return "no receipt";
  if (digest.certify_score === null) return digest.verdict;
  return `${digest.verdict} ${Math.round(digest.certify_score)}/100`;
}

export function badgeJson(digest: ReceiptDigest | null): {
  schemaVersion: 1;
  label: string;
  message: string;
  color: string;
  cacheSeconds: number;
} {
  return {
    schemaVersion: 1,
    label: "forge certify",
    message: badgeMessageFor(digest),
    color: badgeColorFor(digest?.certify_score ?? null, digest?.verdict ?? "?"),
    cacheSeconds: 300,
  };
}

export function renderSvg(digest: ReceiptDigest | null): string {
  const label = "forge certify";
  const message = badgeMessageFor(digest);
  const color = badgeColorFor(
    digest?.certify_score ?? null,
    digest?.verdict ?? "?",
  );
  return shieldsIoSvg(label, message, color);
}

// Canonical 6-character-monospace shields.io badge layout. Width
// computed by 6.5px-per-glyph + 6px padding on each side, rounded.
export function shieldsIoSvg(
  label: string,
  message: string,
  color: string,
): string {
  const labelWidth = Math.max(20, label.length * 6 + 12);
  const messageWidth = Math.max(20, message.length * 6 + 12);
  const total = labelWidth + messageWidth;
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${total}" height="20" role="img" aria-label="${escapeXml(label)}: ${escapeXml(message)}">`,
    `<title>${escapeXml(label)}: ${escapeXml(message)}</title>`,
    `<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>`,
    `<clipPath id="r"><rect width="${total}" height="20" rx="3" fill="#fff"/></clipPath>`,
    `<g clip-path="url(#r)">`,
    `<rect width="${labelWidth}" height="20" fill="#555"/>`,
    `<rect x="${labelWidth}" width="${messageWidth}" height="20" fill="${color}"/>`,
    `<rect width="${total}" height="20" fill="url(#s)"/>`,
    `</g>`,
    `<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">`,
    `<text x="${labelWidth / 2}" y="14">${escapeXml(label)}</text>`,
    `<text x="${labelWidth + messageWidth / 2}" y="14">${escapeXml(message)}</text>`,
    `</g>`,
    `</svg>`,
  ].join("");
}

function notFoundSvg(): string {
  return shieldsIoSvg("forge", "404", SHIELD_GREY);
}

function svgHeaders(): Record<string, string> {
  return {
    "Content-Type": "image/svg+xml; charset=utf-8",
    "Cache-Control": "public, max-age=300",
    ...corsHeaders(),
  };
}

function corsHeaders(): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
  };
}

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
