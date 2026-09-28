// hook-cases.test.mjs — runs adapters/hook-cases.json against the JS hook
// CLIs (#475). Twin: adapters/python/hooks/test_hook_cases.py. The twins'
// CLI parity is a data contract: a case lives in the table, not in one
// language's spawn tests, so neither twin can quietly miss it.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
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
const ROW = ["name", "stdin", "stdinHex", "env", "envHex", "cfg", "expectExit", "expectStderr"];
const MODEL = {
  versions: [1],
  meta: ["_doc", "version"],
  fields: Object.fromEntries(Object.keys(HOOKS).map((kind) => [kind, ROW])),
};

// The field types this runner reads. Each row is checked before it runs, so
// both twins refuse the same rows: a null or a number where a string belongs,
// or stdinHex that is not whole hex bytes (Buffer.from would silently
// truncate it), is a table error, not something each language coerces its
// own way. JSON cannot tell 2 from 2.0 here, so the Python twin accepts a
// whole float too. Python twin: _type_problems.
function typeProblems(c) {
  const problems = [];
  for (const f of ["name", "stdin", "stdinHex", "expectStderr"]) {
    if (f in c && typeof c[f] !== "string") problems.push(`${f} must be a string`);
  }
  if (typeof c.stdinHex === "string" && !/^(?:[0-9a-fA-F]{2})*$/.test(c.stdinHex)) {
    problems.push("stdinHex must be whole hex bytes");
  }
  if (!Number.isInteger(c.expectExit)) problems.push("expectExit must be an integer");
  if ("env" in c) {
    if (c.env === null || typeof c.env !== "object" || Array.isArray(c.env)) {
      problems.push("env must be an object");
    } else {
      for (const [k, v] of Object.entries(c.env)) {
        if (v !== null && typeof v !== "string") problems.push(`env.${k} must be a string or null`);
      }
    }
  }
  // envHex sets a variable to raw bytes (#501). The value reaches the hook
  // through `sh` and printf here, whose $(...) strips a trailing newline, so
  // a trailing 0a byte is refused in both twins.
  if ("envHex" in c) {
    if (c.envHex === null || typeof c.envHex !== "object" || Array.isArray(c.envHex)) {
      problems.push("envHex must be an object");
    } else {
      for (const [k, v] of Object.entries(c.envHex)) {
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(k)) problems.push(`envHex key ${JSON.stringify(k)} must be a variable name`);
        if (typeof v !== "string" || !/^(?:[0-9a-fA-F]{2})*$/.test(v)) problems.push(`envHex.${k} must be whole hex bytes`);
        else if (/0a$/i.test(v)) problems.push(`envHex.${k} must not end with a newline byte`);
        else if ((v.match(/../g) ?? []).includes("00")) problems.push(`envHex.${k} must not contain a NUL byte`);
      }
    }
  }
  return problems;
}

// Removed first so the caller's shell cannot leak in: every PLUMBLINE_*
// variable (including ones a later hook adds) and PYTHONIOENCODING.
function isCleared(k) {
  return k.startsWith("PLUMBLINE_") || k === "PYTHONIOENCODING";
}

function run(kind, c) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => !isCleared(k)));
  if (c.cfg !== undefined) env.PLUMBLINE_CFG = JSON.stringify(c.cfg);
  for (const [k, v] of Object.entries(c.env ?? {})) {
    if (v === null) delete env[k];
    else env[k] = v;
  }
  const input = c.stdinHex !== undefined
    ? Buffer.from(c.stdinHex, "hex")
    : Buffer.from(c.stdin ?? "", "utf8");
  const script = fileURLToPath(new URL(HOOKS[kind], import.meta.url));
  const options = { input, env, encoding: "utf8", timeout: 30_000 }; // a hang fails its row
  if (c.envHex === undefined) return spawnSync(process.execPath, [script], options);
  // Node encodes every env value it passes as UTF-8, so raw bytes go through
  // sh: printf writes each byte from an octal escape (#501).
  const exports = Object.entries(c.envHex).map(([k, hex]) => {
    const octal = (hex.match(/../g) ?? []).map((b) => "\\" + parseInt(b, 16).toString(8).padStart(3, "0")).join("");
    return `${k}="$(printf '${octal}')"; export ${k}; `;
  }).join("");
  return spawnSync("sh", ["-c", `${exports}exec "$0" "$1"`, process.execPath, script], options);
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
  it("a planted boolean version fails, as it does in the Python twin", () => {
    const t = { ...structuredClone(cases), version: true };
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown case-table version true")]);
  });
  it("every row's fields have the types this runner reads", () => {
    const problems = Object.keys(HOOKS).flatMap((kind) =>
      (cases[kind] ?? []).flatMap((c) => typeProblems(c).map((p) => `${kind} ${JSON.stringify(c.name)}: ${p}`)));
    expect(problems).toEqual([]);
  });
  it("a planted null or number where a string belongs fails", () => {
    expect(typeProblems({ name: "x", expectExit: 0, stdin: null })).toEqual(["stdin must be a string"]);
    expect(typeProblems({ name: "x", expectExit: 0, env: null })).toEqual(["env must be an object"]);
    expect(typeProblems({ name: "x", expectExit: 0, env: { A: 1 } })).toEqual(["env.A must be a string or null"]);
    expect(typeProblems({ name: "x", expectExit: "2" })).toEqual(["expectExit must be an integer"]);
    expect(typeProblems({ name: "x", expectExit: 2.5 })).toEqual(["expectExit must be an integer"]);
    expect(typeProblems(JSON.parse('{"name": "x", "expectExit": 2.0}'))).toEqual([]);
  });
  it("a planted envHex that is not whole hex bytes, ends in a newline or names no variable fails (#501)", () => {
    expect(typeProblems({ name: "x", expectExit: 0, envHex: { A: "ff0" } })).toEqual(["envHex.A must be whole hex bytes"]);
    expect(typeProblems({ name: "x", expectExit: 0, envHex: { A: "ff0a" } })).toEqual(["envHex.A must not end with a newline byte"]);
    expect(typeProblems({ name: "x", expectExit: 0, envHex: { "A B": "ff" } })).toEqual(["envHex key \"A B\" must be a variable name"]);
    expect(typeProblems({ name: "x", expectExit: 0, envHex: { A: "610062" } })).toEqual(["envHex.A must not contain a NUL byte"]);
  });
  for (const hex of ["efbbb", "1g2c"]) {
    it(`a planted stdinHex that is not whole hex bytes fails (${hex})`, () => {
      expect(typeProblems({ name: "x", expectExit: 0, stdinHex: hex })).toEqual(["stdinHex must be whole hex bytes"]);
    });
  }
  it("every hook has at least one case", () => {
    for (const kind of Object.keys(HOOKS)) expect(cases[kind]?.length, kind).toBeGreaterThan(0);
  });
});

// #474: what counts as a branch name is git's rule, not ours. A row whose
// reason shows how the guard read a named branch (not unset or blank) must
// agree with `git check-ref-format --branch`: "branch unknown" means git
// rejects the name, "on protected branch" means git accepts it. Python twin:
// test_branch_rows_agree_with_git.
function readsBranch(c) {
  const branch = c.env?.PLUMBLINE_BRANCH;
  if (typeof branch !== "string" || !/[^ \t\n\r\f\v]/.test(branch)) return null;
  const reason = c.expectStderr ?? "";
  if (reason.includes("branch unknown")) return { branch, unknown: true };
  if (reason.includes("on protected branch")) return { branch, unknown: false };
  return null;
}

// git runs outside any repository: inside one, `--branch` expands `@{-1}` and
// `@{u}` against that repository's history, so the verdict would depend on
// where the tests run (#474 review).
const OUTSIDE_REPO = mkdtempSync(path.join(os.tmpdir(), "plumb-line-refcheck-"));
const GIT_ENV = { ...process.env, GIT_CEILING_DIRECTORIES: path.dirname(OUTSIDE_REPO) };

describe("hook-cases.json — branch names agree with git (#474)", () => {
  const read = (cases.branchGuard ?? []).map((c) => [c, readsBranch(c)]).filter(([, r]) => r);
  // A change to the reason wording would otherwise select nothing, silently.
  it("selects rows on both sides of git's rule", () => {
    expect(read.filter(([, r]) => r.unknown).length).toBeGreaterThanOrEqual(10);
    expect(read.filter(([, r]) => !r.unknown).length).toBeGreaterThanOrEqual(3);
  });
  for (const [c, { branch, unknown }] of read) {
    it(`${JSON.stringify(branch)}: ${c.name}`, () => {
      const git = spawnSync("git", ["check-ref-format", "--branch", branch], { cwd: OUTSIDE_REPO, env: GIT_ENV });
      expect(git.error, "git did not start").toBeUndefined();
      expect(git.status === 0, "git accepts it as a branch name").toBe(!unknown);
    });
  }
});

for (const kind of Object.keys(HOOKS)) {
  describe(`hook cases — ${kind} CLI`, () => {
    for (const c of cases[kind] ?? []) {
      it(c.name, () => {
        expect(typeProblems(c)).toEqual([]);
        const r = run(kind, c);
        expect(r.error, "the hook did not start, or timed out").toBeUndefined();
        expect(r.status, r.stderr).toBe(c.expectExit);
        if (c.expectStderr !== undefined) expect(r.stderr).toContain(c.expectStderr);
      });
    }
  });
}
