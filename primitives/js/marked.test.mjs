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

  // F2: derive must be no weaker than makeMeta — an out-of-range confidenceScore
  // override is dropped by the same validation, not stored raw.
  it("drops an out-of-range confidenceScore override (F2)", () => {
    const base = mark(100, { source: "real", confidence: "high", confidenceScore: 0.9 });
    const out = derive([base], (b) => b, { confidenceScore: 2 });
    expect("confidenceScore" in out).toBe(false);
  });
  it("keeps a valid confidenceScore override (F2 control)", () => {
    const base = mark(100, { source: "real", confidence: "high", confidenceScore: 0.9 });
    const out = derive([base], (b) => b, { confidenceScore: 0.5 });
    expect(out.confidenceScore).toBe(0.5);
  });
});

describe("envelope immutability (F3)", () => {
  it("freezes lineage steps so recorded history can't be rewritten", () => {
    const base = mark(100, { source: "mock", confidence: "low" });
    const out = derive([base], (b) => b);
    expect(Object.isFrozen(out.lineage[0])).toBe(true);
    expect(() => {
      out.lineage[0].derivedFromMock = false;
    }).toThrow();
    expect(out.lineage[0].derivedFromMock).toBe(true);
  });
  it("a child derive owns a copy of its parent's lineage steps, not a shared ref", () => {
    const base = mark(100, { source: "mock", confidence: "low" });
    const d1 = derive([base], (b) => b);
    const d2 = derive([d1], (b) => b);
    expect(d2.lineage[0]).not.toBe(d1.lineage[0]); // distinct object
    expect(d2.lineage[0].id).toBe(d1.lineage[0].id); // same recorded identity
  });
});
