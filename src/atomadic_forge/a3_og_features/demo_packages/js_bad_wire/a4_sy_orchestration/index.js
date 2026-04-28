// Tier a4 — entry point. May import from a0..a3.

import { echo } from "../a1_at_functions/echo.js";

export default {
  async fetch(request) {
    return new Response(echo("world"));
  },
};
