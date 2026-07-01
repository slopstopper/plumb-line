import { describe, it, expect } from "vitest";
import { auditMeta, validateEnvelope } from "./audit.mjs";
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

  it("flags numeric over-claiming vs lineage scores", () => {
    const meta = {
      source: "derived",
      confidence: "low",
      confidenceScore: 0.9,
      derivedFromMock: false,
      lineage: [{ id: "s1", confidence: "low", confidenceScore: 0.2 }],
    };
    expect(auditMeta(meta).join(" ")).toMatch(/over-claiming: confidenceScore/);
  });
  it("is silent when confidenceScore is at or below the weakest lineage score", () => {
    const meta = {
      source: "derived",
      confidence: "low",
      confidenceScore: 0.2,
      derivedFromMock: false,
      lineage: [{ id: "s1", confidence: "low", confidenceScore: 0.2 }],
    };
    expect(auditMeta(meta)).toEqual([]);
  });
  it("flags a weakestSource cleaner than the lineage proves", () => {
    const meta = {
      source: "derived",
      confidence: "low",
      derivedFromMock: true,
      weakestSource: "real",
      lineage: [{ id: "s1", source: "mock", confidence: "low", derivedFromMock: true }],
    };
    expect(auditMeta(meta).join(" ")).toMatch(/source over-claim/);
  });

  // F1: audit must be no laxer than the combination law. An out-of-enum
  // confidence on a step is laundering, not a free pass — treat it as the floor.
  it("flags over-claim when a lineage step's confidence is out of enum (F1)", () => {
    const meta = {
      source: "derived",
      confidence: "high",
      derivedFromMock: false,
      lineage: [{ id: "s1", confidence: "huge", derivedFromMock: false }],
    };
    expect(auditMeta(meta).join(" ")).toMatch(/over-claiming/);
  });
  it("does not flag when a lineage step records no confidence (F1: no false positive)", () => {
    const meta = {
      source: "derived",
      confidence: "high",
      derivedFromMock: false,
      lineage: [{ id: "s1", derivedFromMock: false }],
    };
    expect(auditMeta(meta).join(" ")).not.toMatch(/over-claiming/);
  });
});

describe("validateEnvelope", () => {
  const VALID = {
    source: "real",
    confidence: "high",
    derivedFromMock: false,
    lineage: [],
  };

  it("is silent on a complete, well-typed envelope", () => {
    expect(validateEnvelope(VALID)).toEqual([]);
  });

  it("is the structural complement to auditMeta: flags {} that auditMeta passes", () => {
    // auditMeta({}) is [] (no claims to contradict); validateEnvelope reports
    // all four required fields missing. The two checkers are complementary.
    expect(auditMeta({})).toEqual([]);
    const issues = validateEnvelope({});
    expect(issues).toHaveLength(4);
    for (const f of ["source", "confidence", "derivedFromMock", "lineage"]) {
      expect(issues.join(" ")).toContain(`required field: ${f}`);
    }
  });

  it("flags a single missing required field", () => {
    const { lineage, ...noLineage } = VALID;
    expect(validateEnvelope(noLineage).join(" ")).toContain(
      "required field: lineage",
    );
  });

  it("flags a present-but-wrong-type field", () => {
    expect(validateEnvelope({ ...VALID, lineage: "nope" }).join(" ")).toContain(
      "field 'lineage' must be",
    );
    expect(
      validateEnvelope({ ...VALID, derivedFromMock: "false" }).join(" "),
    ).toContain("field 'derivedFromMock' must be");
  });

  it("is total: returns a list (never throws) for null, undefined, and non-objects", () => {
    expect(validateEnvelope(null)).toEqual(["missing meta"]);
    expect(validateEnvelope(undefined)).toEqual(["missing meta"]);
    expect(validateEnvelope("nope").join(" ")).toContain(
      "not an envelope object",
    );
    expect(validateEnvelope([]).join(" ")).toContain("not an envelope object");
  });
});
