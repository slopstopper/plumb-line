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
