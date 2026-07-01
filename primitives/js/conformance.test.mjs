// conformance.test.mjs — runs the shared cases.json against the JS primitive.
// Its Python twin (primitives/python/test_conformance.py) runs the SAME file;
// together they make JS/Python parity a data contract, not a prose promise.
import { describe, it, expect, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { combineProvenance, __resetStepCounter } from "./provenance.mjs";
import { auditMeta, validateEnvelope } from "./audit.mjs";

const cases = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../conformance/cases.json", import.meta.url)),
    "utf8",
  ),
);

beforeEach(() => __resetStepCounter());

describe("conformance — combine", () => {
  for (const c of cases.combine) {
    it(c.name, () => {
      const out = combineProvenance(...c.inputs);
      for (const [k, v] of Object.entries(c.expect)) {
        expect(out[k]).toEqual(v);
      }
      for (const k of c.absent || []) {
        expect(k in out).toBe(false);
      }
    });
  }
});

describe("conformance — audit", () => {
  for (const c of cases.audit) {
    it(c.name, () => {
      const issues = auditMeta(c.meta);
      if (c.expectContains.length === 0) {
        expect(issues).toEqual([]);
      } else {
        for (const needle of c.expectContains) {
          expect(issues.some((i) => i.includes(needle))).toBe(true);
        }
      }
    });
  }
});

describe("conformance — validate", () => {
  for (const c of cases.validate) {
    it(c.name, () => {
      const issues = validateEnvelope(c.meta);
      if (c.expectContains.length === 0) {
        expect(issues).toEqual([]);
      } else {
        for (const needle of c.expectContains) {
          expect(issues.some((i) => i.includes(needle))).toBe(true);
        }
      }
    });
  }
});
