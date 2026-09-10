// primitives/js/baseline.conformance.test.mjs — runs baseline-cases.json against the JS baseline.
// Twin: primitives/python/tests/test_baseline_conformance.py. Parity is a data contract.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { compare, summarize, canonicalJson } from "./baseline.mjs";

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
      expect(JSON.parse(text)).toEqual(JSON.parse(c.expect));
      if (!/\d\.\d/.test(c.expect)) expect(text).toBe(c.expect);
    });
  }
});
