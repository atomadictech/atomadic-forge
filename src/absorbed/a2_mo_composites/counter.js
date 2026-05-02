// Tier a2 — stateful Counter. May import from a0 + a1.

import { DEFAULT_START_VALUE, MAX_INCREMENT } from "../a0_qk_constants/messages.js";
import { clampDelta } from "../a1_at_functions/format_count.js";

export class Counter {
  constructor(start = DEFAULT_START_VALUE) {
    this.value = start;
  }

  increment(delta = 1) {
    const safe = clampDelta(delta, MAX_INCREMENT);
    this.value = this.value + safe;
    return this.value;
  }

  reset() {
    this.value = DEFAULT_START_VALUE;
    return this.value;
  }

  read() {
    return this.value;
  }
}
