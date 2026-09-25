// conformance-runner.test.mjs — the ONE case runner that report.mjs (the
// self-certification gate) and scripts/check-bundle-conformance.mjs (the
// bundled copy) both import (#369). Before it, each had its own copy and they
// had already drifted: report.mjs ignored expectLineageIds.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as impl from "./index.mjs";
import { runCases } from "../conformance/run-cases.mjs";

const cases = JSON.parse(
  readFileSync(fileURLToPath(new URL("../conformance/cases.json", import.meta.url)), "utf8"),
);
const lineageCase = cases.combine.find((c) => c.expectLineageIds);
const only = (combine) => ({ combine, audit: [], validate: [] });

describe("conformance runner (shared by report.mjs and the bundle check)", () => {
  it("passes every case in cases.json against the reference implementation", () => {
    const results = runCases(impl, cases);
    expect(results.length).toBe(cases.combine.length + cases.audit.length + cases.validate.length);
    expect(results.filter((r) => r.error)).toEqual([]);
  });

  it("fails a combine case whose expectLineageIds do not match", () => {
    const wrong = { ...lineageCase, expectLineageIds: ["sha256:000000000000"] };
    const [r] = runCases(impl, only([wrong]));
    expect(r.error).toMatch(/lineage ids/);
  });

  it("fails a case carrying a field the runner does not interpret", () => {
    // The drift class #369 names: a new case field one runner reads and
    // another silently ignores. Unknown fields are an error, never a pass.
    const extra = { ...cases.combine[0], expectSomethingNew: true };
    const [r] = runCases(impl, only([extra]));
    expect(r.error).toMatch(/unknown case field.*expectSomethingNew/);
  });
});
