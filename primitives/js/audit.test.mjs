import { describe, it, expect } from "vitest";
import { auditMeta, validateEnvelope } from "./audit.mjs";
import { mark, derive, metaOf } from "./marked.mjs";
import {
  __resetStepCounter,
  PROVENANCE_VERSION,
  makeMeta,
} from "./provenance.mjs";

describe("auditMeta", () => {
  it("is silent on a consistent clean meta", () => {
    expect(
      auditMeta({
        provenanceVersion: PROVENANCE_VERSION,
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
  it("returns only the version-legacy advisory for an empty meta object (#93: absent version is legacy)", () => {
    expect(auditMeta({})).toEqual([
      `version-legacy: envelope predates version ${PROVENANCE_VERSION}`,
    ]);
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
      provenanceVersion: PROVENANCE_VERSION,
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

  // #93: version read policy — forgiving forward, honest backward.
  it("current version → no version issue", () => {
    const issues = auditMeta(makeMeta({ source: "real" }));
    expect(issues.some((i) => i.startsWith("version-"))).toBe(false);
  });

  it("legacy (absent version) → version-legacy", () => {
    const issues = auditMeta({ source: "real", confidence: "high", derivedFromMock: false, lineage: [] });
    expect(issues.some((i) => i.startsWith("version-legacy:"))).toBe(true);
  });

  it("unknown future version → version-future (still passes, advisory)", () => {
    const issues = auditMeta({ provenanceVersion: 99, source: "real", confidence: "high", derivedFromMock: false, lineage: [] });
    expect(issues.some((i) => i.startsWith("version-future:"))).toBe(true);
  });

  it("pins the version-malformed advisory string SPEC.md documents verbatim", () => {
    // SPEC.md §5 quotes this sentence exactly, and consumers prefix-match the
    // code. Python asserts the full string in test_audit.py; conformance only
    // matches the `version-malformed:` prefix, so without this the JS wording
    // could drift from the SPEC and from Python with every gate still green.
    for (const bad of ["2", null, [], {}, true, Infinity, -Infinity, NaN]) {
      expect(
        auditMeta({ provenanceVersion: bad, source: "real", confidence: "high", derivedFromMock: false, lineage: [] }),
      ).toEqual(["version-malformed: provenance version is not a finite number"]);
    }
  });

  it("a huge integer version arriving via JSON lands in the malformed branch (#225)", () => {
    // Cross-language claim, half pinned per side: Python's
    // test_audit_meta_is_total_on_a_huge_integer_version pins the arbitrary-
    // precision int('9'*400) half; its docstring STATES the JSON.parse →
    // Infinity half, and this test is the executable form of that statement.
    // cases.json cannot express non-finite numbers, so neither half can live
    // in the shared table.
    const meta = JSON.parse(
      `{"provenanceVersion": ${"9".repeat(400)}, "source": "real", "confidence": "high", "derivedFromMock": false, "lineage": []}`,
    );
    expect(meta.provenanceVersion).toBe(Infinity);
    expect(auditMeta(meta)).toEqual(["version-malformed: provenance version is not a finite number"]);
  });

  it("a fractional version is malformed; an integral float is valid (#216)", () => {
    // SPEC §5b carries an integer, judged on the VALUE: "predates version 2"
    // said of 1.5 asserts contract-conformance it lacks, and 2.5 is no more a
    // future version than "3" is. JSON has no int/float distinction, so 2.0
    // must stay a valid current version in both languages.
    const at = (v) => auditMeta({ provenanceVersion: v, source: "real", confidence: "high", derivedFromMock: false, lineage: [] });
    expect(at(2.5)).toEqual(["version-malformed: provenance version is not an integer"]);
    expect(at(1.5)).toEqual(["version-malformed: provenance version is not an integer"]);
    expect(at(2.0)).toEqual([]);
  });

  it("audits a non-plain object as missing meta (#96 parity with Python)", () => {
    expect(auditMeta(new Date())).toEqual(["missing meta"]);
    expect(auditMeta(new Map())).toEqual(["missing meta"]);
    class Box {}
    expect(auditMeta(new Box())).toEqual(["missing meta"]);
    expect(auditMeta(Object.create(null))).toEqual(["missing meta"]);
  });
  it("still audits a plain object envelope normally", () => {
    // A structurally empty plain object has no claims to contradict — its
    // only issue is the pre-existing version-legacy advisory (#93), since
    // {} carries no provenanceVersion. It is not "missing meta".
    expect(auditMeta({})).toEqual([
      `version-legacy: envelope predates version ${PROVENANCE_VERSION}`,
    ]);
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

  it("is the structural complement to auditMeta: flags {} that auditMeta mostly passes", () => {
    // auditMeta({}) has no logical claims to contradict — its only issue is the
    // version-legacy advisory (#93), since {} carries no provenanceVersion.
    // validateEnvelope reports all four required fields missing. The two
    // checkers are complementary.
    expect(auditMeta({})).toEqual([
      `version-legacy: envelope predates version ${PROVENANCE_VERSION}`,
    ]);
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
