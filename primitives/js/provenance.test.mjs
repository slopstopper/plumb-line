import { describe, it, expect } from "vitest";
import { STATUS, CONFIDENCE, makeMeta } from "./provenance.mjs";

describe("constants", () => {
  it("orders status least->most trustworthy", () => {
    expect(STATUS).toEqual([
      "unavailable",
      "mock",
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
  it("applies defaults", () => {
    const m = makeMeta({});
    expect(m.source).toBe("derived");
    expect(m.confidence).toBe("none");
    expect(m.derivedFromMock).toBe(false);
    expect(m.lineage).toEqual([]);
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

import { combineProvenance, __resetStepCounter } from "./provenance.mjs";
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
    expect(out.lineage[0].id).toBe("step-1");
  });
  it("accumulates prior lineage from inputs", () => {
    const withHistory = { ...real, lineage: [{ id: "old", of: "prior" }] };
    const out = combineProvenance(withHistory, semi);
    expect(out.lineage.some((s) => s.id === "old")).toBe(true);
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
  it("returns a sane clean meta for zero inputs", () => {
    const out = combineProvenance();
    expect(out.derivedFromMock).toBe(false);
    expect(out.confidence).toBe("none");
    expect(out.source).toBe("derived");
    expect(out.lineage).toEqual([]);
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
