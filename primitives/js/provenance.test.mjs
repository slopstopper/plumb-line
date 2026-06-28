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
