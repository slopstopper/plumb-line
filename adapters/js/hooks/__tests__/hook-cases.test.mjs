// hook-cases.test.mjs — runs adapters/hook-cases.json against the JS hook
// CLIs (#475). Twin: adapters/python/hooks/test_hook_cases.py. The twins'
// CLI parity is a data contract: a case lives in the table, not in one
// language's spawn tests, so neither twin can quietly miss it.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { tableProblems } from "../../../../primitives/conformance/table-guards.mjs";

const cases = JSON.parse(readFileSync(
  fileURLToPath(new URL("../../../hook-cases.json", import.meta.url)), "utf8"));

const HOOKS = {
  branchGuard: "../branch-guard.mjs",
  boundaryGuard: "../boundary-guard.mjs",
  preCommitGate: "../pre-commit-gate.mjs",
};

// Every field, case kind and table version this runner interprets (#441).
// Python twin: _MODEL in adapters/python/hooks/test_hook_cases.py.
const ROW = ["name", "stdin", "stdinHex", "env", "cfg", "expectExit", "expectStderr"];
const MODEL = {
  versions: [1],
  meta: ["_doc", "version"],
  fields: Object.fromEntries(Object.keys(HOOKS).map((kind) => [kind, ROW])),
};

// Variables a row may set; removed first so the caller's shell cannot leak in.
const CLEARED = ["PLUMBLINE_BRANCH", "PLUMBLINE_CFG", "PLUMBLINE_TEST_CMD", "PYTHONIOENCODING"];

function run(kind, c) {
  const env = { ...process.env };
  for (const k of CLEARED) delete env[k];
  if (c.cfg !== undefined) env.PLUMBLINE_CFG = JSON.stringify(c.cfg);
  for (const [k, v] of Object.entries(c.env ?? {})) {
    if (v === null) delete env[k];
    else env[k] = v;
  }
  const input = c.stdinHex !== undefined
    ? Buffer.from(c.stdinHex, "hex")
    : Buffer.from(c.stdin ?? "", "utf8");
  const script = fileURLToPath(new URL(HOOKS[kind], import.meta.url));
  return spawnSync(process.execPath, [script], { input, env, encoding: "utf8" });
}

describe("hook-cases.json — the runner interprets every field, kind and version", () => {
  it("the shipped table has nothing this runner ignores", () => {
    expect(tableProblems(cases, MODEL)).toEqual([]);
  });
  it("a planted unknown field fails", () => {
    const t = structuredClone(cases);
    t.branchGuard[0].surprise = 1;
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown field(s) surprise")]);
  });
  it("a planted unknown kind fails", () => {
    const t = { ...structuredClone(cases), commitMsgGuard: [] };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case kind commitMsgGuard")]);
  });
  it("a planted unknown version fails", () => {
    const t = { ...structuredClone(cases), version: 2 };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case-table version 2")]);
  });
  it("every hook has at least one case", () => {
    for (const kind of Object.keys(HOOKS)) expect(cases[kind]?.length, kind).toBeGreaterThan(0);
  });
});

for (const kind of Object.keys(HOOKS)) {
  describe(`hook cases — ${kind} CLI`, () => {
    for (const c of cases[kind] ?? []) {
      it(c.name, () => {
        const r = run(kind, c);
        expect(r.error, "the hook did not start").toBeUndefined();
        expect(r.status, r.stderr).toBe(c.expectExit);
        if (c.expectStderr !== undefined) expect(r.stderr).toContain(c.expectStderr);
      });
    }
  });
}
