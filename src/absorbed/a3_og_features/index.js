// Tier a4 — Cloudflare-Worker-style entry point. May import from a0..a3.

import { makeCounter, bump } from "../a3_og_features/counter_feature.js";
import { COUNTER_RESET_TEXT } from "../a0_qk_constants/messages.js";

const counter = makeCounter(0);

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/reset") {
      counter.reset();
      return new Response(COUNTER_RESET_TEXT);
    }
    const text = bump(counter, 1);
    return new Response(text);
  },

  async scheduled(event, env, ctx) {
    counter.reset();
  },
};
