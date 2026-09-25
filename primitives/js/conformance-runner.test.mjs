// conformance-runner.test.mjs — the ONE case runner that report.mjs (the
// self-certification gate) and scripts/check-bundle-conformance.mjs (the
// bundled copy) both import (#369). Before it, each had its own copy and they
// had already drifted: report.mjs ignored expectLineageIds.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import * as impl from "./index.mjs";
import { runCases, describeCaseTable } from "../conformance/run-cases.mjs";

const CASES_PATH = fileURLToPath(new URL("../conformance/cases.json", import.meta.url));
const REPORT = fileURLToPath(new URL("../conformance/report.mjs", import.meta.url));
const cases = JSON.parse(readFileSync(CASES_PATH, "utf8"));
const lineageCase = cases.combine.find((c) => c.expectLineageIds);
const only = (combine) => ({ version: cases.version, combine, audit: [], validate: [] });

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

  it("fails a case-table version the runner does not model (#433)", () => {
    const results = runCases(impl, { ...only([]), version: 2 });
    expect(results.filter((r) => r.error).map((r) => r.error)).toEqual([
      expect.stringMatching(/unknown case-table version 2/),
    ]);
  });

  it("describes the case table a verdict was earned on (#433)", () => {
    const table = describeCaseTable(cases, readFileSync(CASES_PATH));
    expect(table.version).toBe(cases.version);
    expect(table.counts).toEqual({
      combine: cases.combine.length, audit: cases.audit.length, validate: cases.validate.length,
    });
    expect(table.sha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it("report.mjs --json records the case table next to the verdict (#433)", () => {
    const out = JSON.parse(execFileSync("node", [REPORT, "--json"], { encoding: "utf8" }));
    expect(out.caseTable).toEqual(describeCaseTable(cases, readFileSync(CASES_PATH)));
    expect(out.ok).toBe(true);
  });

  it("the human report names the case table too (#433)", () => {
    const out = execFileSync("node", [REPORT], { encoding: "utf8" });
    expect(out).toMatch(/case table v1, sha256:[0-9a-f]{12}/);
  });

  it("fails a case kind the runner does not interpret", () => {
    // Same drift class one level up: a new top-level kind in cases.json was
    // skipped by every runner, and the gate still said CONFORMANT.
    const results = runCases(impl, { ...only([]), derive: [{ name: "x" }] });
    expect(results.filter((r) => r.error).map((r) => r.error)).toEqual([
      expect.stringMatching(/unknown case kind.*derive/),
    ]);
  });
});
