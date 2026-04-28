// Tier a1 — pure formatter. May import from a0 only.

import { COUNTER_OK } from "../a0_qk_constants/messages.js";

export function formatCount(value) {
  return `${COUNTER_OK}: ${value}`;
}

export function clampDelta(delta, max) {
  if (delta > max) {
    return max;
  }
  if (delta < -max) {
    return -max;
  }
  return delta;
}
