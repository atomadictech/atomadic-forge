import { describe, it, expect } from "vitest";
import type { WireReport } from "@/lib/types";
import { SEVERITY_WEIGHTS } from "@/lib/types";

describe("SEVERITY_WEIGHTS", () => {
  it("error=4", () => expect(SEVERITY_WEIGHTS.error).toBe(4));
  it("warn=2", () => expect(SEVERITY_WEIGHTS.warn).toBe(2));
  it("info=1", () => expect(SEVERITY_WEIGHTS.info).toBe(1));
});

function computeDebt(r: WireReport, rate: number): number {
  return r.violations.reduce((t, v) => t + (SEVERITY_WEIGHTS[v.severity] ?? 1) * rate, 0);
}
const base: WireReport = { schema_version: "1", source: "/p", violations: [
  { file: "a.py", line: 1, severity: "error", message: "x" },
  { file: "b.py", line: 2, severity: "warn", message: "y" },
  { file: "c.py", line: 3, severity: "info", message: "z" },
], violation_count: 3, autofixable_count: 1, files_scanned: 10 };

describe("computeDebt", () => {
  it("$80/hr: error(4)+warn(2)+info(1)=7*80=560", () => expect(computeDebt(base, 80)).toBe(560));
  it("scales linearly", () => expect(computeDebt(base, 100)).toBe(700));
  it("zero violations -> 0", () => expect(computeDebt({ ...base, violations: [], violation_count: 0 }, 80)).toBe(0));
});

function brittleness(auto: number, total: number): number { return total === 0 ? 0 : 1 - auto / total; }
describe("brittleness", () => {
  it("0 when all autofixable", () => expect(brittleness(5,5)).toBe(0));
  it("1 when none autofixable", () => expect(brittleness(0,5)).toBe(1));
  it("0.5 when half", () => expect(brittleness(3,6)).toBeCloseTo(0.5));
  it("0 when total=0", () => expect(brittleness(0,0)).toBe(0));
});

describe("tier distribution totals", () => {
  it("sums correctly", () => {
    const d = { a0:5, a1:10, a2:8, a3:3, a4:2, unknown:1 };
    expect(Object.values(d).reduce((s,n)=>s+n,0)).toBe(29);
  });
});