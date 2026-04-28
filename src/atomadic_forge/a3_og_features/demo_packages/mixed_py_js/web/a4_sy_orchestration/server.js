// Tier a4 — Cloudflare-Worker-style entry. May import a0..a3.

import { formatStatus } from "../a1_at_functions/format_status.js";

export default {
  async fetch(request) {
    const text = formatStatus("ok", "mixed-pyjs-up");
    return new Response(text);
  },
};
