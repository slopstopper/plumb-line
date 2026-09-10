import { describe, it, expect } from "vitest";
import {
  canonicalJson, compactJson, deepEqual, isJsonValue,
  compare, summarize, BASELINE_FORMAT, NAME_RE,
} from "./baseline.mjs";

const step = (over = {}) => ({
  id: "sha256:000000000000", of: "input", source: "real", confidence: "high",
  derivedFromMock: false, confidenceScore: 0.9, ...over,
});
const meta = (over = {}) => ({
  provenanceVersion: 2, source: "derived", confidence: "high", derivedFromMock: false,
  confidenceScore: 0.9, lineage: [step(), step({ id: "sha256:111111111111" })], ...over,
});
const record = (over = {}) => ({
  "baseline-format": BASELINE_FORMAT, name: "nightly-rate", provenanceVersion: 2,
  value: 0.0412, meta: meta(), history: [{ date: "2026-09-10", because: "initial pin", change: "initial" }],
  ...over,
});

describe("canonical JSON", () => {
  it("sorts keys recursively and keeps array order", () => {
    expect(canonicalJson({ b: 1, a: { d: [3, { z: 1, y: 2 }], c: 0 } }))
      .toBe('{\n  "a": {\n    "c": 0,\n    "d": [\n      3,\n      {\n        "y": 2,\n        "z": 1\n      }\n    ]\n  },\n  "b": 1\n}\n');
  });
  it("compact form renders booleans and null", () => {
    expect(compactJson(true)).toBe("true");
    expect(compactJson(undefined)).toBe("null");
    expect(compactJson({ b: [1, "x"], a: null })).toBe('{"a":null,"b":[1,"x"]}');
  });
  it("isJsonValue rejects what cannot round-trip", () => {
    expect(isJsonValue({ a: [1, "b", null, true] })).toBe(true);
    for (const bad of [undefined, () => 1, NaN, Infinity, 10n]) expect(isJsonValue(bad)).toBe(false);
    const cyc = {}; cyc.self = cyc;
    expect(isJsonValue(cyc)).toBe(false);
  });
  it("deepEqual compares structure, not identity", () => {
    expect(deepEqual({ a: [1, { b: 2 }] }, { a: [1, { b: 2 }] })).toBe(true);
    expect(deepEqual({ a: 1 }, { a: 1, b: 2 })).toBe(false);
    expect(deepEqual([1, 2], [2, 1])).toBe(false);
    expect(deepEqual(1, 1.0)).toBe(true);
  });
  it("NAME_RE accepts safe names only", () => {
    expect(NAME_RE.test("nightly-rate.v2_x")).toBe(true);
    for (const bad of ["../x", "a b", "a/b", "", "é"]) expect(NAME_RE.test(bad)).toBe(false);
  });
});

describe("compare — attribution", () => {
  it("identical pin and envelope yield no findings", () => {
    expect(compare(record(), meta(), 0.0412, 2)).toEqual([]);
  });
  it("a moved step field is named by position and field", () => {
    const m = meta({ lineage: [step(), step({ id: "sha256:222222222222", source: "fallback" })] });
    const f = compare(record(), m, 0.0412, 2);
    expect(f).toEqual([{ path: "meta.lineage[1].source", before: "real", after: "fallback",
                         text: 'meta.lineage[1].source: "real" -> "fallback"' }]);
  });
  it("ids are never diffed", () => {
    const m = meta({ lineage: [step({ id: "sha256:aaaaaaaaaaaa" }), step({ id: "sha256:bbbbbbbbbbbb" })] });
    expect(compare(record(), m, 0.0412, 2)).toEqual([]);
  });
  it("lineage growth names the first new step, shrinkage the first missing one", () => {
    const grew = compare(record(), meta({ lineage: [step(), step(), step()] }), 0.0412, 2);
    expect(grew).toEqual([{ path: "meta.lineage.length", before: 2, after: 3,
                            text: "lineage grew by 1 (first new step: meta.lineage[2])" }]);
    const shrank = compare(record(), meta({ lineage: [step()] }), 0.0412, 2);
    expect(shrank[0].text).toBe("lineage shrank by 1 (first missing step: meta.lineage[1])");
  });
  it("a top-level field is reported only when no lineage finding touched that field", () => {
    // confidence moved at step 1 AND at the top: one finding, the step's.
    const m = meta({ confidence: "medium", lineage: [step(), step({ confidence: "medium" })] });
    const f = compare(record(), m, 0.0412, 2);
    expect(f.map((x) => x.path)).toEqual(["meta.lineage[1].confidence"]);
    // confidence moved at the top with NO lineage finding: reported at the top.
    const g = compare(record(), meta({ confidence: "medium" }), 0.0412, 2);
    expect(g).toEqual([{ path: "meta.confidence", before: "high", after: "medium",
                         text: 'meta.confidence: "high" -> "medium"' }]);
  });
  it("value moved with no input change is its own finding", () => {
    expect(compare(record(), meta(), 0.05, 2)).toEqual([
      { path: "value", before: 0.0412, after: 0.05, text: "value moved with no input change" }]);
  });
  it("value moved alongside trust findings is attributed to them", () => {
    const f = compare(record(), meta({ confidence: "low" }), 0.05, 2);
    expect(f.map((x) => x.text)).toEqual([
      'meta.confidence: "high" -> "low"', "value moved; attributed to the findings above"]);
  });
  it("trust drift with an unchanged value is still drift", () => {
    expect(compare(record(), meta({ derivedFromMock: true }), 0.0412, 2)).toHaveLength(1);
  });
  it("a wire version mismatch is the first finding", () => {
    const f = compare(record({ provenanceVersion: 1 }), meta(), 0.0412, 2);
    expect(f[0]).toEqual({ path: "provenanceVersion", before: 1, after: 2,
                           text: "pinned under wire v1, running v2" });
  });
  it("findings come in the fixed order: version, steps, length, top-level, value", () => {
    const m = meta({ confidence: "low", derivedFromMock: true,
                     lineage: [step({ source: "mock", derivedFromMock: true })] });
    const paths = compare(record({ provenanceVersion: 1 }), m, 1, 2).map((x) => x.path);
    expect(paths).toEqual(["provenanceVersion", "meta.lineage[0].source", "meta.lineage[0].derivedFromMock",
                           "meta.lineage.length", "meta.confidence", "value"]);
  });
  it("summarize joins texts with '; '", () => {
    expect(summarize([{ text: "a" }, { text: "b" }])).toBe("a; b");
    expect(summarize([])).toBe("none");
  });
});
