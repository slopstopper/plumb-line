// long-lineage.test.mjs — combine, audit and guard are total on a very long
// lineage (#560). An argument spread over a lineage (`f(...lineage.map(...))`,
// `Math.min(...scores)`) passes one argument per step, and past about 100,000
// arguments JS throws `RangeError: Maximum call stack size exceeded`, where
// Python's min() over a list does not. SPEC §5 requires the checker to be
// total, and the two languages must agree. The same lineage and the same
// expected results are in the Python twin, tests/test_long_lineage.py.
import { describe, it, expect } from "vitest";
import { makeMeta, combineProvenance, combineConfidenceScore, auditMeta, guard, ProvenanceRefused, mark, derive } from "./index.mjs";

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

// A sparse lineage (#560 review). reduce, every, some and forEach skip an
// array's holes, where a spread read each as undefined, so a hole could pass
// the guard and go unnamed by the audit. Python has no holes; its twin is a
// None step, and both must give the same results.
describe("a lineage with a hole (#560 review)", () => {
  // eslint-disable-next-line no-sparse-arrays
  const holed = makeMeta({ source: "derived", confidence: "high", derivedFromMock: false, weakestSource: "real", lineage: [, strong] });

  it("is audited as a step that is not an object", () => {
    expect(auditMeta(holed)).toEqual([
      "source over-claim: weakestSource 'real' cannot be shown: a lineage step's source is unknown",
      "unknown source: lineage step 0 is not an object",
    ]);
  });

  it("is refused by the guard as an invalid envelope, with or without a confidence floor", () => {
    for (const options of [{ minConfidence: "high" }, {}]) {
      expect(reasons(() => guard(mark(1, holed), options))).toEqual([
        "invalid envelope: lineage step 0 is not a plain object",
      ]);
    }
  });

  it("gives no combined score over a gap, and no throw", () => {
    // eslint-disable-next-line no-sparse-arrays
    expect(combineConfidenceScore([0.5, , 0.3])).toBeUndefined();
    expect(combineConfidenceScore(new Array(2))).toBeUndefined();
  });

  it("keeps the hole through combine, as Python keeps a None step", () => {
    const c = combineProvenance(holed);
    expect([c.lineage.length, 0 in c.lineage, c.lineage[0], "weakestSource" in c]).toEqual([3, true, undefined, false]);
    expect(auditMeta(c)).toEqual(["unknown source: lineage step 0 is not an object"]);
  });

  it("is refused by the guard after a derive, with or without a confidence floor", () => {
    const d = derive([mark(1, holed)], (v) => v);
    for (const options of [{ minConfidence: "high" }, {}]) {
      expect(reasons(() => guard(d, options))).toEqual([
        "invalid envelope: lineage step 0 is not a plain object",
      ]);
    }
  });
});

// A lineage whose own iterator yields other steps than its indices hold (#560
// review, JS only: a Python list has no such split). The guard and the audit
// read the lineage by index, once, so what is validated is what is judged.
describe("a lineage whose iterator disagrees with its indices (#560 review)", () => {
  const bad = { ...strong, derivedFromMock: "yes" };
  const lineage = [bad];
  Object.defineProperty(lineage, Symbol.iterator, { value: function* () { yield strong; } });
  const value = { ...mark(1, makeMeta({ source: "derived", confidence: "high", derivedFromMock: false, weakestSource: "real", lineage: [strong] })), lineage };

  it("is judged by what its indices hold", () => {
    expect(auditMeta(value)).toContain("malformed taint flag: lineage step 0 derivedFromMock is not a boolean");
    expect(reasons(() => guard(value, {}))).toContain("invalid envelope: lineage step 0 derivedFromMock must be a boolean");
  });
});
