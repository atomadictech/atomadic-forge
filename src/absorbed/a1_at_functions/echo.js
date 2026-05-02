// Tier a1 — pure helpers. The LAW says: a1 may import a0 ONLY.
//
// THIS FILE INTENTIONALLY VIOLATES THAT LAW.
//
// The import below pulls in `formatGreeting` from a3_og_features.
// `forge wire` will surface this as an upward-import violation with
// `language: "javascript"` so the demo can teach what the scanner
// catches.
//
// To fix it for real you would either move `formatGreeting` down
// to a1 (if it's pure), or move `echo` up to a3 (if it really needs
// the feature-tier helper).

import { formatGreeting } from "../a3_og_features/feature.js";  // <-- ILLEGAL: a1 ⟵ a3
import { ECHO_OK } from "../a0_qk_constants/messages.js";

export function echo(text) {
  return `${ECHO_OK}: ${formatGreeting(text)}`;
}
