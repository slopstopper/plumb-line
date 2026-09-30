import { describe, it, test, expect } from "vitest";
import {
  STATUS,
  CONFIDENCE,
  makeMeta,
  combineProvenance,
  PROVENANCE_VERSION,
  stepId,
} from "./provenance.mjs";
import { auditMeta } from "./audit.mjs";
import { guard, ProvenanceRefused } from "./guard.mjs";

test("PROVENANCE_VERSION is 2", () => {
  expect(PROVENANCE_VERSION).toBe(2);
});

test("makeMeta stamps the current provenanceVersion", () => {
  expect(makeMeta({ source: "real" }).provenanceVersion).toBe(2);
});

test("combineProvenance output carries provenanceVersion", () => {
  const out = combineProvenance(makeMeta({ source: "real" }));
  expect(out.provenanceVersion).toBe(2);
});

describe("constants", () => {
  it("orders status least->most trustworthy", () => {
    expect(STATUS).toEqual([
      "unavailable",
      "mock",
      "inferred",
      "fallback",
      "semiReal",
      "derived",
      "real",
    ]);
  });
  it("orders confidence weakest->strongest", () => {
    expect(CONFIDENCE).toEqual(["none", "low", "medium", "high"]);
  });
});

describe("makeMeta", () => {
  it("applies defaults to everything but source", () => {
    const m = makeMeta({ source: "real" });
    expect(m.confidence).toBe("none");
    expect(m.derivedFromMock).toBe(false);
    expect(m.lineage).toEqual([]);
  });
  // A leaf has no parents, so "derived" was never true of it (#177).
  it.each([
    ["no options at all", undefined],
    ["an empty options object", {}],
    ["an explicit undefined source", { source: undefined, confidence: "low" }],
  ])("refuses a missing source: %s", (_label, opts) => {
    expect(() => makeMeta(opts)).toThrow(
      "source is required (one of unavailable, mock, inferred, fallback, semiReal, derived, real)");
  });
  it("infers derivedFromMock from a mock source", () => {
    expect(makeMeta({ source: "mock" }).derivedFromMock).toBe(true);
  });
  it("respects an explicit derivedFromMock over inference", () => {
    expect(
      makeMeta({ source: "real", derivedFromMock: true }).derivedFromMock,
    ).toBe(true);
  });
  it("omits undefined optional fields", () => {
    const m = makeMeta({ source: "real" });
    expect("basis" in m).toBe(false);
    expect("adapter" in m).toBe(false);
  });
});

import { weakestConfidence, taints } from "./provenance.mjs";

describe("weakestConfidence", () => {
  it("returns the weakest level", () => {
    expect(weakestConfidence("high", "low", "medium")).toBe("low");
  });
  it("returns none for no args", () => {
    expect(weakestConfidence()).toBe("none");
  });
  it("treats an unknown level as none", () => {
    expect(weakestConfidence("high", "bogus")).toBe("none");
  });
});

describe("taints", () => {
  it("is true for a mock source", () => {
    expect(taints({ source: "mock", derivedFromMock: false })).toBe(true);
  });
  it("is true when derivedFromMock is set", () => {
    expect(taints({ source: "real", derivedFromMock: true })).toBe(true);
  });
  it("is false for a clean meta", () => {
    expect(taints({ source: "real", derivedFromMock: false })).toBe(false);
  });
});

import { __resetStepCounter } from "./provenance.mjs";
import { beforeEach } from "vitest";

beforeEach(() => __resetStepCounter());

const real = {
  source: "real",
  confidence: "high",
  derivedFromMock: false,
  lineage: [],
};
const mock = {
  source: "mock",
  confidence: "low",
  derivedFromMock: true,
  lineage: [],
};
const semi = {
  source: "semiReal",
  confidence: "medium",
  derivedFromMock: false,
  lineage: [],
};

describe("combineProvenance — the law", () => {
  it("taints when any input is mock (OR)", () => {
    expect(combineProvenance(real, mock).derivedFromMock).toBe(true);
  });
  it("stays clean when all inputs are clean", () => {
    expect(combineProvenance(real, semi).derivedFromMock).toBe(false);
  });
  it("degrades confidence to the weakest input", () => {
    expect(combineProvenance(real, semi).confidence).toBe("medium");
    expect(combineProvenance(real, mock).confidence).toBe("low");
  });
  it("labels the result source as derived", () => {
    expect(combineProvenance(real, semi).source).toBe("derived");
  });
  it("is order-independent for taint and confidence", () => {
    const a = combineProvenance(real, mock);
    __resetStepCounter();
    const b = combineProvenance(mock, real);
    expect(a.derivedFromMock).toBe(b.derivedFromMock);
    expect(a.confidence).toBe(b.confidence);
  });
  it("records a lineage step per input capturing its trust", () => {
    const out = combineProvenance(real, mock);
    expect(out.lineage).toHaveLength(2);
    expect(out.lineage[1]).toMatchObject({
      source: "mock",
      confidence: "low",
      derivedFromMock: true,
    });
    expect(out.lineage[0].id).toMatch(/^sha256:/);
  });
  it("accumulates prior lineage from inputs", () => {
    // Inherited steps are carried into the output verbatim, keeping their
    // original content-addressed id — they are never renumbered (#52).
    const withHistory = { ...real, lineage: [{ id: "old", of: "prior" }] };
    const out = combineProvenance(withHistory, semi);
    expect(out.lineage.some((s) => s.of === "prior")).toBe(true);
  });
  it("taints from a mock source even when the input flag is false", () => {
    const sneaky = {
      source: "mock",
      confidence: "low",
      derivedFromMock: false,
      lineage: [],
    };
    const clean = {
      source: "real",
      confidence: "high",
      derivedFromMock: false,
      lineage: [],
    };
    expect(combineProvenance(clean, sneaky).derivedFromMock).toBe(true);
  });
  it("ORs taint across three or more inputs", () => {
    const clean = {
      source: "real",
      confidence: "high",
      derivedFromMock: false,
      lineage: [],
    };
    const mock = {
      source: "mock",
      confidence: "low",
      derivedFromMock: true,
      lineage: [],
    };
    expect(combineProvenance(clean, clean, mock).derivedFromMock).toBe(true);
  });
  it("returns an 'unavailable' meta for zero inputs (derived from nothing)", () => {
    // A value combined from no inputs is derived from nothing — 'unavailable',
    // not 'derived'. 'derived' would contradict auditMeta's "derived value has
    // no lineage" check (SPEC §3 vs §5). See #25.
    const out = combineProvenance();
    expect(out.derivedFromMock).toBe(false);
    expect(out.confidence).toBe("none");
    expect(out.source).toBe("unavailable");
    expect(out.lineage).toEqual([]);
  });
  it("assigns identical, reproducible content-addressed step IDs across repeated combines", () => {
    // No module-level counter: two independent combines with identical inputs
    // produce identical step ids, since ids are a pure function of content. See #23.
    const first = combineProvenance(real, mock);
    const second = combineProvenance(real, mock);
    expect(first.lineage.map((s) => s.id)).toEqual(second.lineage.map((s) => s.id));
    expect(first.lineage.every((s) => s.id.startsWith("sha256:"))).toBe(true);
  });
  it("dedups identical sub-lineages by design when both inputs carry the same history (SPEC §4)", () => {
    // Two independently-built envelopes with identical content produce identical
    // ids for their steps — that collision is intended dedup, not an error,
    // because it means "the same derivation happened twice." See #52.
    const a = combineProvenance(real, mock);
    const b = combineProvenance(real, mock);
    const out = combineProvenance(a, b);
    expect(out.lineage).toHaveLength(6);
    // a's and b's inherited steps carry the same content -> same ids.
    expect(out.lineage[0].id).toBe(out.lineage[2].id);
    expect(out.lineage[1].id).toBe(out.lineage[3].id);
    expect(out.lineage.every((s) => s.id.startsWith("sha256:"))).toBe(true);
  });
  test("input-step id is stable across recombination", () => {
    const a = { source: "real", confidence: "high", derivedFromMock: false, lineage: [] };
    const once = combineProvenance(a);
    const twice = combineProvenance(a, { source: "mock", confidence: "low", derivedFromMock: true, lineage: [] });
    // the input step summarizing `a` has the same id in both outputs
    const idInOnce = once.lineage.find((s) => s.source === "real").id;
    const idInTwice = twice.lineage.find((s) => s.source === "real").id;
    expect(idInOnce).toBe(idInTwice);
  });
  test("combine no longer emits sequential step-N ids", () => {
    const out = combineProvenance({ source: "real", confidence: "high", derivedFromMock: false, lineage: [] });
    expect(out.lineage.every((s) => s.id.startsWith("sha256:"))).toBe(true);
  });
  it("handles a single input", () => {
    const real = {
      source: "real",
      confidence: "high",
      derivedFromMock: false,
      lineage: [],
    };
    const out = combineProvenance(real);
    expect(out.derivedFromMock).toBe(false);
    expect(out.lineage).toHaveLength(1);
  });
  it("tolerates a meta missing keys ({})", () => {
    const out = combineProvenance({});
    expect(out.source).toBe("derived");
    expect(out.derivedFromMock).toBe(false);
  });
});

import {
  weakestSource,
  combineConfidenceScore,
  isScore,
} from "./provenance.mjs";

describe("weakestSource", () => {
  it("returns the least-trustworthy source by STATUS rank", () => {
    expect(weakestSource("real", "mock", "semiReal")).toBe("mock");
    expect(weakestSource("real", "semiReal")).toBe("semiReal");
  });
  it("ignores unknown values", () => {
    expect(weakestSource("real", "bogus")).toBe("real");
  });
  it("returns undefined when nothing is rankable", () => {
    expect(weakestSource()).toBeUndefined();
    expect(weakestSource("bogus")).toBeUndefined();
  });
});

describe("isScore / combineConfidenceScore", () => {
  it("accepts only finite numbers in [0,1]", () => {
    expect(isScore(0)).toBe(true);
    expect(isScore(1)).toBe(true);
    expect(isScore(0.5)).toBe(true);
    expect(isScore(1.1)).toBe(false);
    expect(isScore(-0.1)).toBe(false);
    expect(isScore("0.5")).toBe(false);
    expect(isScore(NaN)).toBe(false);
  });
  it("takes the minimum only when every input has a score", () => {
    expect(combineConfidenceScore([0.9, 0.2, 0.6])).toBe(0.2);
    expect(combineConfidenceScore([0.9, undefined])).toBeUndefined();
    expect(combineConfidenceScore([])).toBeUndefined();
  });
});

describe("combineProvenance — new fields", () => {
  const realScored = {
    source: "real",
    confidence: "high",
    confidenceScore: 0.9,
    derivedFromMock: false,
    lineage: [],
  };
  const mockScored = {
    source: "mock",
    confidence: "low",
    confidenceScore: 0.2,
    derivedFromMock: true,
    lineage: [],
  };
  it("floors confidenceScore to the weakest input", () => {
    expect(combineProvenance(realScored, mockScored).confidenceScore).toBe(0.2);
  });
  it("omits confidenceScore when any input lacks one", () => {
    const out = combineProvenance(realScored, { source: "real", confidence: "high" });
    expect("confidenceScore" in out).toBe(false);
  });
  it("records the weakest source across the ancestry", () => {
    expect(combineProvenance(realScored, mockScored).weakestSource).toBe("mock");
  });
  it("omits weakestSource for zero inputs", () => {
    expect("weakestSource" in combineProvenance()).toBe(false);
  });
  it("records confidenceScore on a lineage step when the input has one", () => {
    const out = combineProvenance(realScored, mockScored);
    expect(out.lineage[0].confidenceScore).toBe(0.9);
    expect(out.lineage[1].confidenceScore).toBe(0.2);
  });
  it("omits confidenceScore from a step whose input lacks one", () => {
    const out = combineProvenance(realScored, { source: "real", confidence: "high" });
    expect("confidenceScore" in out.lineage[1]).toBe(false);
  });
});

test("inferred sits between mock and fallback", () => {
  expect(STATUS.indexOf("mock")).toBeLessThan(STATUS.indexOf("inferred"));
  expect(STATUS.indexOf("inferred")).toBeLessThan(STATUS.indexOf("fallback"));
});

test("combine picks inferred as weakest over fallback", () => {
  const out = combineProvenance(
    makeMeta({ source: "fallback", confidence: "low" }),
    makeMeta({ source: "inferred", confidence: "low" }),
  );
  expect(out.weakestSource).toBe("inferred");
});

test("stepId is a stable sha256 short id for a known leaf step", () => {
  const step = { of: "input", source: "real", confidence: "high", derivedFromMock: false };
  expect(stepId(step, [])).toBe("sha256:097181b20233");
});

test("stepId is stable regardless of input-id order (sorted)", () => {
  const step = { of: "input", source: "real", confidence: "high", derivedFromMock: false };
  expect(stepId(step, ["b", "a"])).toBe(stepId(step, ["a", "b"]));
});


// #525 review: what the case table cannot express.
describe("combineProvenance reads source and confidence as it reads taint (#525 review)", () => {
  it("through the prototype: an envelope built by Object.create keeps its source on the step", () => {
    const m = Object.create({ source: "mock", confidence: "high", derivedFromMock: true, lineage: [] });
    const out = combineProvenance(m, makeMeta({ source: "real", confidence: "high" }));
    expect(out.lineage[0].source).toBe("mock");
    expect(out.lineage[0].confidence).toBe("high");
    expect(out.weakestSource).toBe("mock");
    expect(out.derivedFromMock).toBe(true);
  });
  it("records null for a field the input does not have, so every step has both keys", () => {
    const out = combineProvenance({ derivedFromMock: false, lineage: [] }, "x");
    for (const step of out.lineage) {
      expect(step).toHaveProperty("source", null);
      expect(step).toHaveProperty("confidence", null);
    }
  });
});

// #548: a prior step's fields are copied as the law reads them, through the
// prototype. A copy of own fields only let a step's inherited taint be
// cleared by one combine. JSON cannot build such a step, so no case row.
describe("makeMeta copies a lineage step's inherited fields (#548)", () => {
  const INHERITED_TAINT = () =>
    Object.assign(Object.create({ derivedFromMock: true }), {
      of: "input", source: "real", confidence: "high", id: "sha256:000000000001",
    });
  // The envelope's own flag is false, so the tainted step is a finding.
  const envelopeWith = (step) => ({
    provenanceVersion: PROVENANCE_VERSION, source: "derived", confidence: "high",
    derivedFromMock: false, weakestSource: "real", lineage: [step],
  });

  it("inherited taint survives combineProvenance, the audit flags it and the guard refuses", () => {
    const out = combineProvenance(envelopeWith(INHERITED_TAINT()));
    expect(out.lineage[0].derivedFromMock).toBe(true);
    expect(auditMeta(out)).toContain(
      "taint dropped: lineage contains a tainted step but derivedFromMock is false",
    );
    const value = { value: 1, ...out };
    expect(() => guard(value)).toThrow(ProvenanceRefused);
  });

  it("an inherited source survives the copy", () => {
    const step = Object.assign(Object.create({ source: "mock" }), {
      of: "input", confidence: "high", derivedFromMock: false, id: "sha256:000000000002",
    });
    const meta = makeMeta({ source: "derived", confidence: "high", lineage: [step] });
    expect(meta.lineage[0].source).toBe("mock");
  });

  it("the copy is a plain frozen object, and an own field wins over an inherited one", () => {
    const step = Object.assign(Object.create({ derivedFromMock: true, source: "mock" }), {
      of: "input", source: "real", confidence: "high", derivedFromMock: false,
    });
    const copy = makeMeta({ source: "derived", lineage: [step] }).lineage[0];
    expect(Object.getPrototypeOf(copy)).toBe(Object.prototype);
    expect(Object.isFrozen(copy)).toBe(true);
    expect(copy.source).toBe("real");
    expect(copy.derivedFromMock).toBe(false);
  });

  it("a law field that is not enumerable is kept too", () => {
    const step = Object.defineProperty(
      { of: "input", source: "real", confidence: "high" },
      "derivedFromMock", { value: true, enumerable: false },
    );
    const copy = makeMeta({ source: "derived", lineage: [step] }).lineage[0];
    expect(copy.derivedFromMock).toBe(true);
    expect(Object.keys(copy)).toContain("derivedFromMock");
  });

  it("a polluted Object.prototype is not copied into a step (it is no step's own)", () => {
    // Baked into a frozen copy, a polluted source would outlive the pollution
    // and survive JSON, where a step with no source is refused.
    try {
      Object.prototype.source = "real";
      const copy = makeMeta({ source: "derived", lineage: [{ of: "input", confidence: "high" }] }).lineage[0];
      expect(Object.hasOwn(copy, "source")).toBe(false);
    } finally {
      delete Object.prototype.source;
    }
  });

  it("an own field that is not enumerable still shadows an inherited one", () => {
    const step = Object.defineProperty(
      Object.assign(Object.create({ note: "inherited" }), { of: "input", source: "real" }),
      "note", { value: "own", enumerable: false },
    );
    const copy = makeMeta({ source: "derived", lineage: [step] }).lineage[0];
    expect(Object.hasOwn(copy, "note")).toBe(false);
  });

  it("an inherited __proto__ key is copied as a field, never as the copy's prototype", () => {
    // JSON.parse makes "__proto__" an own key; as a prototype, it is inherited.
    const proto = JSON.parse('{"__proto__": {"derivedFromMock": true}}');
    const step = Object.assign(Object.create(proto), { of: "input", source: "real" });
    const copy = makeMeta({ source: "derived", lineage: [step] }).lineage[0];
    expect(Object.getPrototypeOf(copy)).toBe(Object.prototype);
    expect(Object.hasOwn(copy, "__proto__")).toBe(true);
    expect(copy.derivedFromMock).toBeUndefined();
  });
});
