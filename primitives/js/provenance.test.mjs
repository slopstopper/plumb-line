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
