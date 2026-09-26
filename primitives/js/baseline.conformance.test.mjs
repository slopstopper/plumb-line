// primitives/js/baseline.conformance.test.mjs — runs baseline-cases.json against the JS baseline.
// Twin: primitives/python/tests/test_baseline_conformance.py. Parity is a data contract.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { compare, summarize, canonicalJson, validateBaseline } from "./baseline.mjs";
import { tableProblems } from "../conformance/table-guards.mjs";

const cases = JSON.parse(readFileSync(
  fileURLToPath(new URL("../conformance/baseline-cases.json", import.meta.url)), "utf8"));

// Every field, case kind and table version this runner interprets (#441), the
// guards cases.json has had since #369 and #433. `_expectBytes` is the table's
// inline note on `expectBytes`, read by people, not runners. Python twin:
// _MODEL in primitives/python/tests/test_baseline_conformance.py.
const MODEL = {
  versions: [1],
  meta: ["_doc", "version"],
  fields: {
    attribute: ["name", "record", "meta", "value", "runningVersion", "expectFindings", "expectSummary"],
    canonical: ["name", "input", "expect", "expectBytes", "_expectBytes"],
    validate: ["name", "record", "expectContains"],
  },
};

describe("baseline-cases.json — the runner interprets every field, kind and version", () => {
  it("the shipped table has nothing this runner ignores", () => {
    expect(tableProblems(cases, MODEL)).toEqual([]);
  });
  it("a planted unknown field fails", () => {
    const t = structuredClone(cases);
    t.validate[0].surprise = 1;
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown field(s) surprise")]);
  });
  it("a planted unknown kind fails", () => {
    const t = { ...structuredClone(cases), drift: [] };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case kind drift")]);
  });
  it("a planted unknown version fails", () => {
    const t = { ...structuredClone(cases), version: 2 };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case-table version 2")]);
  });
  it("a planted boolean version fails, as it does in the Python twin", () => {
    const t = { ...structuredClone(cases), version: true };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case-table version true")]);
  });
});

describe("baseline conformance — attribute", () => {
  for (const c of cases.attribute) {
    it(c.name, () => {
      const f = compare(c.record, c.meta, c.value, c.runningVersion);
      expect(f).toEqual(c.expectFindings);
      expect(summarize(f)).toBe(c.expectSummary);
    });
  }
});

describe("baseline conformance — canonical", () => {
  for (const c of cases.canonical) {
    it(c.name, () => {
      const text = canonicalJson(c.input);
      // Parsed equality is the contract in every case; byte-exactness is a
      // stronger claim the case table makes explicitly, rather than a runner
      // guessing from the shape of the expected text.
      expect(JSON.parse(text)).toEqual(JSON.parse(c.expect));
      if (c.expectBytes !== false) expect(text).toBe(c.expect);
    });
  }
});

describe("baseline conformance — validate", () => {
  for (const c of cases.validate) {
    it(c.name, () => {
      const issues = validateBaseline(c.record);
      if (c.expectContains.length === 0) expect(issues).toEqual([]);
      for (const needle of c.expectContains) expect(issues.some((i) => i.includes(needle))).toBe(true);
    });
  }
});
