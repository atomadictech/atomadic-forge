// Tier a3 — counter feature. Composes a1 + a2.

import { Counter } from "../a2_mo_composites/counter.js";
import { formatCount } from "../a1_at_functions/format_count.js";

export function makeCounter(start) {
  return new Counter(start);
}

export function bump(counter, delta) {
  counter.increment(delta);
  return formatCount(counter.read());
}
