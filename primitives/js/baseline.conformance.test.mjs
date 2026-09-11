// primitives/js/baseline.conformance.test.mjs — runs baseline-cases.json against the JS baseline.
// Twin: primitives/python/tests/test_baseline_conformance.py. Parity is a data contract.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { compare, summarize, canonicalJson, validateBaseline } from "./baseline.mjs";

const cases = JSON.parse(readFileSync(
  fileURLToPath(new URL("../conformance/baseline-cases.json", import.meta.url)), "utf8"));

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
