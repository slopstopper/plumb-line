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

// #443: mark and a derive override build on makeMeta, so they refuse an
// off-ladder rung or source too. Python twin: the #443 tests in test_marked.py.
describe("mark / derive refuse an off-ladder confidence or source (#443)", () => {
  it("mark refuses a numeric confidence", () => {
    expect(() => mark(1, { source: "mock", confidence: 0 })).toThrow(
      "confidence must be one of none, low, medium, high; got 0");
  });
  it("mark refuses a source outside STATUS", () => {
    expect(() => mark(1, { source: "bogus" })).toThrow(/^source must be one of unavailable, mock/);
  });
  it("mark refuses a missing source (#177)", () => {
    expect(() => mark(1)).toThrow(/^source is required \(one of unavailable/);
    expect(() => mark(1, { confidence: "high" })).toThrow(/^source is required/);
  });
  it("an undefined source override on derive is no override (#177)", () => {
    // derive is not a leaf: its source comes from the combination law, so an
    // undefined override keeps it rather than tripping the leaf rule.
    const a = mark(1, { source: "real", confidence: "high" });
    const out = derive([a], (x) => x, { source: undefined });
    expect(out.source).toBe("derived");
    expect(derive([], () => 0, { source: undefined }).source).toBe("unavailable");
  });
  it("a derive override is refused the same way", () => {
    const a = mark(1, { source: "real", confidence: "high" });
    expect(() => derive([a], (x) => x, { confidence: 0.8 })).toThrow(
      "confidence must be one of none, low, medium, high; got 0.8");
  });
  // A value JSON.stringify cannot write must not replace the refusal with a
  // serialisation error, and NaN must not read as null (#443 review).
  const cyclic = {};
  cyclic.self = cyclic;
  it.each([
    [1n, "got 1"],
    [cyclic, "got [object Object]"],
    [NaN, "got NaN"],
    [Infinity, "got Infinity"],
  ])("the refusal message survives an unusual value (%s)", (confidence, tail) => {
    expect(() => mark(1, { source: "real", confidence })).toThrow(
      `confidence must be one of none, low, medium, high; ${tail}`);
  });
});

describe("derive: an undefined override is no override (#533)", () => {
  it.each(["source", "confidence", "confidenceScore", "basis", "adapter"])(
    "an undefined %s override on derive is no override (#533)",
    (key) => {
      // A caller writing derive(xs, f, { confidence: opts.confidence }) with
      // the option unset must keep the law's result, not reset or drop it.
      const a = mark(1, { source: "real", confidence: "high", confidenceScore: 0.9 });
      const b = mark(2, { source: "fallback", confidence: "medium", confidenceScore: 0.6 });
      const plain = derive([a, b], (x, y) => x + y);
      const out = derive([a, b], (x, y) => x + y, { [key]: undefined });
      expect(out).toEqual(plain);
      expect(Object.keys(out)).toEqual(Object.keys(plain));
    },
  );
  it("reads each override value once, so a getter cannot reset the rung", () => {
    const a = mark(1, { source: "real", confidence: "high" });
    let reads = 0;
    const override = { get confidence() { return reads++ === 0 ? "low" : undefined; } };
    expect(derive([a], (x) => x, override).confidence).toBe("low");
  });
  it.each(["source", "confidence"])("a null %s override is still refused (#443, not #533)", (key) => {
    // undefined is no override; null is a value, and off the ladder.
    const a = mark(1, { source: "real", confidence: "high" });
    expect(() => derive([a], (x) => x, { [key]: null })).toThrow(`${key} must be one of`);
  });
});


describe("derive refuses a derivedFromMock override that is not a boolean (#555, reversing #525)", () => {
  it("throws, as the Python twin raises; true still taints, false and null leave a clean input clean", () => {
    const clean = mark(1, { source: "real", confidence: "high" });
    for (const flag of [[], {}, 0, "", "false", "true"]) {
      expect(() => derive([clean], (v) => v, { derivedFromMock: flag })).toThrow("derivedFromMock must be a boolean");
    }
    // Values JSON.stringify cannot write, or writes as null, are refused with
    // makeMeta's own message and quoting (#555 review).
    const cycle = [];
    cycle.push(cycle);
    for (const flag of [10n, NaN, cycle, Symbol("s"), () => 1]) {
      let error;
      try { derive([clean], (v) => v, { derivedFromMock: flag }); } catch (e) { error = e; }
      expect(error?.message).toMatch(/^derivedFromMock must be a boolean; got /);
      expect(error.message).not.toMatch(/got (null|undefined)$/);
    }
    expect(derive([clean], (v) => v, { derivedFromMock: true }).derivedFromMock).toBe(true);
    for (const flag of [false, null]) {
      expect(derive([clean], (v) => v, { derivedFromMock: flag }).derivedFromMock).toBe(false);
    }
  });
});


describe("derive refuses an input that is not a marked value (#550)", () => {
  // A marked value as the guard reads one: a plain object holding `value`.
  // JS used to combine an unmarked object or null as an unknown input and
  // throw an unrelated TypeError on a number; Python raised on all three.
  const clean = mark(1, { source: "real", confidence: "high" });
  class Box { constructor() { this.value = 1; } }
  for (const [label, input] of [["an object", { a: 1 }], ["null", null], ["a number", 3],
    ["an array", [1]], ["a class instance", new Box()], ["undefined", undefined]]) {
    it(`refuses ${label}, naming its position, before calling fn`, () => {
      let called = false;
      expect(() => derive([clean, input], () => { called = true; }))
        .toThrow(new TypeError("derive: input 1 is not a marked value (mark it first)"));
      expect(called).toBe(false);
    });
  }
  it("still accepts marked values, including a handed one with an empty envelope", () => {
    expect(derive([clean], (v) => v + 1).value).toBe(2);
    expect(derive([{ value: 2 }], (v) => v).lineage[0].source).toBe(null);
  });
});

describe("derive reads its inputs once, as a list (#550 review)", () => {
  const mock = mark(41, { source: "mock", confidence: "low" });
  const clean = mark(1, { source: "real", confidence: "high" });
  it("a generator of marked values keeps their taint (it was combined as zero inputs)", () => {
    function* gen() { yield mock; }
    const out = derive(gen(), (v) => v + 1);
    expect(out.value).toBe(42);
    expect(out.derivedFromMock).toBe(true);
    expect(out.source).toBe("derived");
  });
  it("a hole in a sparse array is refused like undefined", () => {
    // eslint-disable-next-line no-sparse-arrays
    expect(() => derive([, clean], () => 0)).toThrow("derive: input 0 is not a marked value (mark it first)");
  });
  it("a Set is read in order, naming the real position", () => {
    expect(() => derive(new Set([clean, 3]), () => 0)).toThrow("derive: input 1 is not a marked value (mark it first)");
  });
  for (const [label, inputs] of [["a number", 3], ["null", null], ["a string", "ab"], ["a plain object", { a: clean }]]) {
    it(`refuses ${label} as the inputs`, () => {
      expect(() => derive(inputs, () => 0)).toThrow(new TypeError("derive: inputs must be a list of marked values"));
    });
  }
});
