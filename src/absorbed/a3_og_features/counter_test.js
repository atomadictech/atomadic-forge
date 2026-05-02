// JS test — recognised by forge certify (tests/*.test.js).
// Authored as a Vitest-shape file; readable on its own.

import { Counter } from "../a2_mo_composites/counter.js";
import { formatCount, clampDelta } from "../a1_at_functions/format_count.js";
import { bump, makeCounter } from "../a3_og_features/counter_feature.js";

export function testCounterStartsAtZero() {
  const c = new Counter();
  if (c.read() !== 0) throw new Error("counter did not start at 0");
}

export function testCounterIncrements() {
  const c = makeCounter(10);
  c.increment(5);
  if (c.read() !== 15) throw new Error("counter did not increment");
}

export function testFormatCount() {
  if (formatCount(7) !== "ok: 7") throw new Error("format mismatch");
}

export function testClampDelta() {
  if (clampDelta(2_000, 1_000) !== 1_000) throw new Error("clamp upper failed");
  if (clampDelta(-2_000, 1_000) !== -1_000) throw new Error("clamp lower failed");
}

export function testBump() {
  const c = makeCounter(0);
  if (bump(c, 3) !== "ok: 3") throw new Error("bump did not return ok: 3");
}
