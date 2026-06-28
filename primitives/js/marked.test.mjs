import { describe, it, expect, beforeEach } from "vitest";
import { mark, unwrap, metaOf, derive } from "./marked.mjs";
import { combineProvenance, __resetStepCounter } from "./provenance.mjs";

beforeEach(() => __resetStepCounter());

describe("mark / unwrap", () => {
  it("wraps a value with normalized meta", () => {
    const m = mark(100, { source: "real", confidence: "high" });
    expect(m.value).toBe(100);
    expect(m.source).toBe("real");
    expect(m.derivedFromMock).toBe(false);
  });
  it("unwrap returns the value", () => {
    expect(unwrap(mark(42, { source: "real" }))).toBe(42);
  });
});

describe("derive", () => {
  it("computes the value via fn over unwrapped inputs", () => {
    const base = mark(100, { source: "real", confidence: "high" });
    const rate = mark(0.029, { source: "mock", confidence: "low" });
    const total = derive([base, rate], (b, r) => b * (1 + r));
    expect(total.value).toBeCloseTo(102.9);
    expect(total.derivedFromMock).toBe(true);
    expect(total.confidence).toBe("low");
  });
  it("meta equals combineProvenance for the same inputs (wrapper is a shim)", () => {
    const a = mark(1, { source: "real", confidence: "high" });
    const b = mark(2, { source: "semiReal", confidence: "medium" });
    const viaDerive = metaOf(derive([a, b], (x, y) => x + y));
    __resetStepCounter();
    const viaLaw = combineProvenance(metaOf(a), metaOf(b));
    expect(viaDerive).toEqual(viaLaw);
  });
  it("a source override cannot clear the mock taint", () => {
    const clean = mark(1, { source: "real", confidence: "high" });
    const dirty = mark(2, { source: "mock", confidence: "low" });
    const out = derive([clean, dirty], (a, b) => a + b, { source: "real" });
    expect(out.source).toBe("real");
    expect(out.derivedFromMock).toBe(true);
  });
  it("lineage key in metaOverride is ignored; computed lineage is used", () => {
    const a = mark(1, { source: "real", confidence: "high" });
    const b = mark(2, { source: "semiReal", confidence: "medium" });
    const out = derive([a, b], (x, y) => x + y, { lineage: [] });
    expect(metaOf(out).lineage.length).toBeGreaterThan(0);
  });
});
