// long-lineage.test.mjs — combine, audit and guard are total on a very long
// lineage (#560). An argument spread over a lineage (`f(...lineage.map(...))`,
// `Math.min(...scores)`) passes one argument per step, and past about 100,000
// arguments JS throws `RangeError: Maximum call stack size exceeded`, where
// Python's min() over a list does not. SPEC §5 requires the checker to be
// total, and the two languages must agree. The same lineage and the same
// expected results are in the Python twin, tests/test_long_lineage.py.
import { describe, it, expect } from "vitest";
import { makeMeta, combineProvenance, auditMeta, guard, ProvenanceRefused, mark } from "./index.mjs";

const N = 200_000;
const WEAK_AT = 150_000;
const strong = combineProvenance(makeMeta({ source: "real", confidence: "high", confidenceScore: 0.9 })).lineage[0];
const weak = combineProvenance(makeMeta({ source: "fallback", confidence: "low", confidenceScore: 0.4 })).lineage[0];
const lineage = Array.from({ length: N }, (_, i) => (i === WEAK_AT ? weak : strong));
const long = makeMeta({
  source: "derived",
  confidence: "low",
  confidenceScore: 0.4,
  derivedFromMock: false,
  weakestSource: "fallback",
  lineage,
});

const reasons = (fn) => {
  try {
    fn();
  } catch (e) {
    if (e instanceof ProvenanceRefused) return e.reasons;
    throw e;
  }
  return "passed";
};

describe("a 200,000-step lineage (#560)", { timeout: 60_000 }, () => {
  it("combines to the weakest confidence, score and source", () => {
    const c = combineProvenance(long);
    expect([c.confidence, c.confidenceScore, c.weakestSource, c.lineage.length]).toEqual(["low", 0.4, "fallback", N + 1]);
  });

  it("audits clean when the headline matches the lineage", () => {
    expect(auditMeta(long)).toEqual([]);
  });

  it("audits each over-claim against the one weak step", () => {
    expect(auditMeta({ ...long, confidence: "high", confidenceScore: 0.9, weakestSource: "real" })).toEqual([
      "over-claiming: confidence 'high' exceeds weakest lineage confidence 'low'",
      "over-claiming: confidenceScore 0.9 exceeds weakest lineage score 0.4",
      "source over-claim: weakestSource 'real' is cleaner than lineage's 'fallback'",
    ]);
  });

  it("guards on the weakest step", () => {
    expect(reasons(() => guard(mark(1, long), { minConfidence: "low" }))).toBe("passed");
    expect(reasons(() => guard(mark(1, long), { minConfidence: "medium" }))).toEqual([
      "confidence: low is below the required medium",
    ]);
    expect(reasons(() => guard(mark(1, long), { minSource: "real" }))).toEqual([
      "source: fallback is below the required real",
    ]);
  });
});
