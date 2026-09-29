// conformance-runner.test.mjs — the ONE case runner that report.mjs (the
// self-certification gate) and scripts/check-bundle-conformance.mjs (the
// bundled copy) both import (#369). Before it, each had its own copy and they
// had already drifted: report.mjs ignored expectLineageIds.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import * as impl from "./index.mjs";
import { runCases, describeCaseTable } from "../conformance/run-cases.mjs";

const CASES_PATH = fileURLToPath(new URL("../conformance/cases.json", import.meta.url));
const REPORT = fileURLToPath(new URL("../conformance/report.mjs", import.meta.url));
const cases = JSON.parse(readFileSync(CASES_PATH, "utf8"));
const lineageCase = cases.combine.find((c) => c.expectLineageIds);
const only = (combine) => ({ version: cases.version, combine, audit: [], validate: [], construct: [], guard: [] });

describe("conformance runner (shared by report.mjs and the bundle check)", () => {
  it("passes every case in cases.json against the reference implementation", () => {
    const results = runCases(impl, cases);
    expect(results.length).toBe(
      cases.combine.length + cases.audit.length + cases.validate.length + cases.construct.length +
      cases.guard.length);
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

  // One negative per judging branch (#430 review): conformance.test.mjs is a
  // thin view over runCases, so a runner that stopped judging would pass
  // vitest, report.mjs and the bundle check at once unless each branch is
  // pinned here to fail on a wrong expectation.
  const plain = cases.combine.find((c) => !c.expectLineageIds && Object.keys(c.expect).length);
  const auditIssue = cases.audit.find((c) => c.expectContains.length);
  const auditClean = cases.audit.find((c) => c.expectContains.length === 0);

  it("fails a combine case whose expect value is wrong", () => {
    const [k] = Object.keys(plain.expect);
    const [r] = runCases(impl, only([{ ...plain, expect: { [k]: "not-a-real-value" } }]));
    expect(r.error).toMatch(new RegExp(`expected ${k}=`));
  });

  it("fails a combine case when a key listed in absent is present", () => {
    const [k] = Object.keys(plain.expect);
    const [r] = runCases(impl, only([{ ...plain, absent: [k] }]));
    expect(r.error).toMatch(new RegExp(`expected ${k} to be absent`));
  });

  // #443: the construct kind fails when makeMeta accepts what the case says it
  // must refuse, refuses with other words, or refuses what it must accept.
  const construct = (c) => ({ version: cases.version, combine: [], audit: [], validate: [], construct: [c], guard: [] });
  it("fails a construct case whose refusal does not happen", () => {
    const [r] = runCases(impl, construct({ name: "x", input: { source: "real", confidence: "high" }, expectError: "must be one of" }));
    expect(r.error).toMatch(/got an envelope/);
  });
  it("fails a construct case whose refusal is worded otherwise", () => {
    const [r] = runCases(impl, construct({ name: "x", input: { source: "real", confidence: 0 }, expectError: "no-such-text" }));
    expect(r.error).toMatch(/expected an error containing "no-such-text"/);
  });
  it("fails a construct case that expects an envelope when makeMeta refuses", () => {
    const [r] = runCases(impl, construct({ name: "x", input: { source: "bogus" }, expect: { source: "bogus" } }));
    expect(r.error).toMatch(/expected an envelope, got an error/);
  });
  it("fails a construct case whose expected field differs", () => {
    const [r] = runCases(impl, construct({ name: "x", input: { source: "real", confidence: "high" }, expect: { confidence: "low" } }));
    expect(r.error).toMatch(/expected confidence="low"/);
  });
  it.each([
    [{ name: "x", input: { source: "real" } }],
    [{ name: "x", input: { source: "real" }, expect: {}, expectError: "must be one of" }],
  ])("fails a construct case without exactly one expectation (%#)", (c) => {
    const [r] = runCases(impl, construct(c));
    expect(r.error).toMatch(/exactly one of expect or expectError/);
  });

  // #120: the guard kind fails a row whose refusal, pass or programmer error
  // does not happen as the row says.
  const clean = { provenanceVersion: 2, source: "real", confidence: "high", derivedFromMock: false, lineage: [] };
  const mockLeaf = { ...clean, source: "mock", confidence: "low", derivedFromMock: true };
  const guardRow = (c) => ({ version: cases.version, combine: [], audit: [], validate: [], construct: [], guard: [c] });
  it("fails a guard case whose refusal does not happen", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: clean, expectRefused: ["mock:"] }));
    expect(r.error).toMatch(/expected a refusal, got a pass/);
  });
  it("fails a guard case whose refusal gives no such reason", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: mockLeaf, expectRefused: ["no-such-reason"] }));
    expect(r.error).toMatch(/expected an issue containing "no-such-reason"/);
  });
  it("fails a guard case whose refusal gives a reason the row says is absent", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: mockLeaf, expectRefused: ["mock:"], expectAbsent: ["mock:"] }));
    expect(r.error).toMatch(/expected no reason containing "mock:"/);
  });
  it("fails a guard case expecting a pass when the value is refused", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: mockLeaf, expectPass: true }));
    expect(r.error).toMatch(/expected a pass, got a refusal/);
  });
  it("fails a guard case that reads a refusal as a programmer error", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: mockLeaf, expectError: "mock" }));
    expect(r.error).toMatch(/expected a programmer error, got a refusal/);
  });
  it("fails a guard pass that returns something other than the value it was given", () => {
    const copying = { ...impl, guard: (x) => ({ ...x }) };
    const [r] = runCases(copying, guardRow({ name: "x", meta: clean, expectPass: true }));
    expect(r.error).toMatch(/must return the marked value it was given/);
  });
  it.each([
    { name: "x", meta: clean },
    { name: "x", meta: clean, expectPass: true, expectError: "y" },
    { name: "x", meta: mockLeaf, expectPass: true, expectAbsent: ["mock:"] },
    { name: "x", meta: mockLeaf, expectPass: false },
    { name: "x", meta: mockLeaf, expectRefused: [] },
  ])("fails a guard case whose expectation is missing, doubled, stray or empty (%#)", (c) => {
    const [r] = runCases(impl, guardRow(c));
    expect(r.error).toMatch(/exactly one of expectPass|expectAbsent is read only|expectPass must be true|at least one reason/);
  });
  it("fails a guard case expecting a refusal when the guard raises a programmer error", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: clean, options: { minConfidence: "hi" }, expectRefused: ["mock:"] }));
    expect(r.error).toMatch(/expected a refusal, got an error/);
  });
  it("fails a guard case whose programmer error is worded otherwise", () => {
    const [r] = runCases(impl, guardRow({ name: "x", meta: clean, options: { minConfidence: "hi" }, expectError: "no-such-text" }));
    expect(r.error).toMatch(/expected an error containing "no-such-text"/);
  });
  it("fails a guard case whose programmer error is a supertype of the refusal", () => {
    const loose = { ...impl, guard: () => { throw new Error("guard: bad option"); } };
    const [r] = runCases(loose, guardRow({ name: "x", meta: clean, expectError: "guard: bad option" }));
    expect(r.error).toMatch(/must not be a supertype of the refusal/);
  });
  it.each([
    { name: "x", meta: mockLeaf, expectRefused: [""] },
    { name: "x", meta: mockLeaf, expectRefused: ["mock:"], expectAbsent: [""] },
    { name: "x", meta: clean, options: { minConfidence: "hi" }, expectError: "" },
  ])("fails a guard case with an empty needle (%#)", (c) => {
    const [r] = runCases(impl, guardRow(c));
    expect(r.error).toMatch(/non-empty string/);
  });
  // The runner judges a thrown value on its prototype chain, whatever its
  // `constructor` says, and must not crash on it. A null-prototype object is
  // unrelated to the refusal, so it conforms (SPEC §5c); a plain object has
  // Object.prototype, a supertype of the refusal, however it fakes its
  // `constructor`.
  it("judges a null-prototype thrown value as unrelated to the refusal", () => {
    const odd = { ...impl, guard: () => { throw Object.assign(Object.create(null), { message: "guard: x" }); } };
    const [r] = runCases(odd, guardRow({ name: "x", meta: clean, expectError: "guard: x" }));
    expect(r.error).toBeNull();
  });
  it.each([
    () => ({ message: "guard: x", constructor: 1 }),
    () => ({ message: "guard: x", constructor: () => 0 }),
    () => ({ message: "guard: x", constructor: TypeError }),
  ])("fails a plain thrown object as a supertype of the refusal, whatever its constructor says (%#)", (make) => {
    const odd = { ...impl, guard: () => { throw make(); } };
    const [r] = runCases(odd, guardRow({ name: "x", meta: clean, expectError: "guard: x" }));
    expect(r.error).toMatch(/must not be a supertype of the refusal/);
  });
  it.each([
    () => ({ message: Object.create(null) }),
    () => ({ message: Symbol("x") }),
    () => ({ get message() { throw 1; } }),
    () => new Proxy({}, { getPrototypeOf() { throw new Error("trap"); } }),
  ])("fails, rather than crashes, on a thrown value it cannot inspect, on any row (%#)", (make) => {
    const odd = { ...impl, guard: () => { throw make(); } };
    for (const row of [{ name: "x", meta: clean, expectPass: true },
      { name: "x", meta: mockLeaf, expectRefused: ["mock:"] },
      { name: "x", meta: clean, expectError: "guard: x" }]) {
      const results = runCases(odd, guardRow(row));
      expect(results).toHaveLength(1);
      expect(results[0].error).toEqual(expect.any(String));
    }
  });
  it("fails a guard case whose expectAbsent is not a list of reasons", () => {
    for (const expectAbsent of ["zzz", []]) {
      const [r] = runCases(impl, guardRow({ name: "x", meta: mockLeaf, expectRefused: ["mock:"], expectAbsent }));
      expect(r.error).toMatch(/expectAbsent must list at least one reason/);
    }
  });
  it("fails, rather than crashes, on an implementation without ProvenanceRefused", () => {
    const { ProvenanceRefused: _dropped, ...partial } = impl;
    const [r] = runCases(partial, guardRow({ name: "x", meta: mockLeaf, expectRefused: ["mock:"] }));
    expect(r.error).toMatch(/exports no ProvenanceRefused/);
  });

  it("fails a table that lacks a kind the runner models", () => {
    const { construct: _dropped, ...rest } = cases;
    const results = runCases(impl, rest);
    expect(results.filter((r) => r.error)).toEqual([
      { kind: "construct", name: "(whole kind)", error: "case kind construct is missing from the table" },
    ]);
  });

  it("fails an audit case whose needle no issue contains", () => {
    const [r] = runCases(impl, { version: cases.version, combine: [], validate: [], construct: [], guard: [],
      audit: [{ ...auditIssue, expectContains: ["no-such-issue-text"] }] });
    expect(r.error).toMatch(/expected an issue containing "no-such-issue-text"/);
  });

  it("fails an audit case expecting no issues when there are some", () => {
    const [r] = runCases(impl, { version: cases.version, combine: [], validate: [], construct: [], guard: [],
      audit: [{ ...auditIssue, expectContains: [] }] });
    expect(r.error).toMatch(/expected no issues/);
    const [ok] = runCases(impl, { version: cases.version, combine: [], validate: [], construct: [], guard: [],
      audit: [auditClean] });
    expect(ok.error).toBeNull();
  });

  it("compares expect values by deep equality, so key order does not matter", () => {
    // JSON.stringify comparison depends on key order: a correct expectation
    // written with its keys in another order failed. Build the true lineage,
    // reverse each step's keys, and expect it to pass.
    impl.__resetStepCounter();
    const truth = impl.combineProvenance(...plain.inputs).lineage;
    const reordered = truth.map((s) => Object.fromEntries(Object.entries(s).reverse()));
    const [r] = runCases(impl, only([{ ...plain, expect: { ...plain.expect, lineage: reordered } }]));
    expect(r.error).toBeNull();
  });

  it("the case-table hash is of the file's exact bytes", () => {
    const bytes = readFileSync(CASES_PATH);
    const independent = createHash("sha256").update(bytes).digest("hex");
    expect(describeCaseTable(cases, bytes).sha256).toBe(independent);
    expect(describeCaseTable(cases, Buffer.from(JSON.stringify(cases))).sha256).not.toBe(independent);
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
      construct: cases.construct.length, guard: cases.guard.length,
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
