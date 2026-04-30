import { describe, it, expect } from "vitest";
import type { WireReport } from "@/lib/types";
import { fCodeSeverity } from "@/lib/types";

describe("fCodeSeverity", () => {
  it("F004x = 4 (structural)", () => expect(fCodeSeverity("F0041")).toBe(4));
  it("F003x = 2 (effect)", () => expect(fCodeSeverity("F0031")).toBe(2));
  it("other = 1", () => expect(fCodeSeverity("F0011")).toBe(1));
});

function computeDebt(r: WireReport, rate: number): number {
  return r.violations.reduce((t, v) => t + fCodeSeverity(v.f_code) * rate, 0);
}
const base: WireReport = { schema_version: "1", source_dir: "/p", violations: [
  { file: "a.py", from_tier: "a1", to_tier: "a3", imported: "X", f_code: "F0041" },
  { file: "b.py", from_tier: "a1", to_tier: "a2", imported: "Y", f_code: "F0031" },
  { file: "c.py", from_tier: "a0", to_tier: "a1", imported: "Z", f_code: "F0011" },
], violation_count: 3, auto_fixable: 1 };

describe("computeDebt", () => {
  it("$80/hr: F004(4)+F003(2)+other(1)=7*80=560", () => expect(computeDebt(base, 80)).toBe(560));
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