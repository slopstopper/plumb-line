import { describe, it, expect } from "vitest";
import { auditMeta } from "./audit.mjs";
import { mark, derive, metaOf } from "./marked.mjs";
import { __resetStepCounter } from "./provenance.mjs";

describe("auditMeta", () => {
  it("is silent on a consistent clean meta", () => {
    expect(
      auditMeta({
        source: "real",
        confidence: "high",
        derivedFromMock: false,
        lineage: [],
      }),
    ).toEqual([]);
  });
  it("flags a clean source with the taint flag set", () => {
    const issues = auditMeta({
      source: "real",
      confidence: "high",
      derivedFromMock: true,
      lineage: [],
    });
    expect(issues.join(" ")).toMatch(/laundering/);
  });
  it("flags over-claiming vs lineage", () => {
    const meta = {
      source: "derived",
      confidence: "high",
      derivedFromMock: false,
      lineage: [{ id: "s1", confidence: "low", derivedFromMock: false }],
    };
    expect(auditMeta(meta).join(" ")).toMatch(/over-claiming/);
  });
  it("flags taint dropped vs lineage", () => {
    const meta = {
      source: "derived",
      confidence: "low",
      derivedFromMock: false,
      lineage: [{ id: "s1", confidence: "low", derivedFromMock: true }],
    };
    expect(auditMeta(meta).join(" ")).toMatch(/taint dropped/);
  });
  it("flags a derived value with no lineage", () => {
    expect(
      auditMeta({
        source: "derived",
        confidence: "low",
        derivedFromMock: false,
        lineage: [],
      }).join(" "),
    ).toMatch(/unreproducible/);
  });

  it("is silent on metadata produced by derive (the law stays consistent)", () => {
    __resetStepCounter();
    const a = mark(1, { source: "real", confidence: "high" });
    const b = mark(2, { source: "mock", confidence: "low" });
    const out = derive([a, b], (x, y) => x + y);
    expect(auditMeta(metaOf(out))).toEqual([]);
  });

  it("does not throw for an invalid top-level confidence, returns an array", () => {
    const result = auditMeta({
      source: "derived",
      confidence: "invalid",
      lineage: [{ confidence: "low", derivedFromMock: false }],
    });
    expect(Array.isArray(result)).toBe(true);
  });
  it("returns [] for an empty meta object", () => {
    expect(auditMeta({})).toEqual([]);
  });
  it("returns ['missing meta'] for null", () => {
    expect(auditMeta(null)).toEqual(["missing meta"]);
  });
});
