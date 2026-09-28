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
const ROW = ["name", "stdin", "stdinHex", "env", "envHex", "repeat", "cfg", "expectExit", "expectStderr"];
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
  // repeat declares long strings instead of writing them out: every
  // {{NAME}} in stdin, env, cfg or expectStderr becomes the string repeated.
  // A token used but not declared, or declared but not used, is a table
  // error, so a typo cannot silently test the literal token instead.
  if ("repeat" in c) {
    if (c.repeat === null || typeof c.repeat !== "object" || Array.isArray(c.repeat)) {
      problems.push("repeat must be an object");
    } else {
      for (const k of Object.keys(c.repeat).sort()) {
        const v = c.repeat[k];
        if (!/^[A-Z][A-Z0-9_]*$/.test(k)) problems.push(`repeat key ${JSON.stringify(k)} must be an upper-case name`);
        if (!Array.isArray(v) || v.length !== 2 || typeof v[0] !== "string" || v[0] === ""
            || !Number.isInteger(v[1]) || v[1] < 1 || v[1] > 1_000_000) {
          problems.push(`repeat.${k} must be [a non-empty string, a count from 1 to 1000000]`);
        } else if (v[0].length * v[1] > 100_000) {
          // Linux caps one environment value at 128 KB (MAX_ARG_STRLEN).
          problems.push(`repeat.${k} must expand to at most 100000 characters`);
        }
      }
    }
  }
  const declared = c.repeat && typeof c.repeat === "object" && !Array.isArray(c.repeat) ? Object.keys(c.repeat).sort() : [];
  if (repeatableStrings(c).some((s) => s.replace(/\{\{[A-Z][A-Z0-9_]*\}\}/g, "").includes("{{"))) {
    problems.push("a repeat token must be written {{UPPER_CASE}}");
  }
  if (repeatableKeys(c).some((k) => k.includes("{{"))) {
    problems.push("repeat tokens are expanded only in values, not keys");
  }
  const used = new Set(repeatTokens(c));
  for (const t of [...used].sort()) if (!declared.includes(t)) problems.push(`repeat token {{${t}}} is not declared`);
  for (const k of declared) if (!used.has(k)) problems.push(`repeat.${k} is not used`);
  return problems;
}

/** Every string a repeat token may appear in: stdin, env values, cfg (deeply), expectStderr. */
function repeatableStrings(c) {
  const out = [];
  const walk = (v) => {
    if (typeof v === "string") out.push(v);
    else if (Array.isArray(v)) v.forEach(walk);
    else if (v !== null && typeof v === "object") Object.values(v).forEach(walk);
  };
  walk([c.stdin, c.env, c.cfg, c.expectStderr]);
  return out;
}

/** Every object key in env and cfg, where tokens are never expanded. */
function repeatableKeys(c) {
  const out = [];
  const walk = (v) => {
    if (Array.isArray(v)) v.forEach(walk);
    else if (v !== null && typeof v === "object") for (const [k, x] of Object.entries(v)) { out.push(k); walk(x); }
  };
  walk([c.env, c.cfg]);
  return out;
}

function repeatTokens(c) {
  return repeatableStrings(c).flatMap((s) => [...s.matchAll(/\{\{([A-Z][A-Z0-9_]*)\}\}/g)].map((m) => m[1]));
}

/** The row with every declared {{NAME}} expanded. Python twin: _expand_repeat. */
function expandRepeat(c) {
  if (c.repeat === undefined) return c;
  const expand = (v) => {
    if (typeof v === "string") {
      return v.replace(/\{\{([A-Z][A-Z0-9_]*)\}\}/g, (m, k) =>
        Object.hasOwn(c.repeat, k) ? c.repeat[k][0].repeat(c.repeat[k][1]) : m);
    }
    if (Array.isArray(v)) return v.map(expand);
    if (v !== null && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, expand(x)]));
    return v;
  };
  const out = { ...c };
  for (const f of ["stdin", "env", "cfg", "expectStderr"]) if (f in c) out[f] = expand(c[f]);
  return out;
}

// Removed first so the caller's shell cannot leak in: every PLUMBLINE_*
// variable (including ones a later hook adds) and PYTHONIOENCODING.
function isCleared(k) {
  return k.startsWith("PLUMBLINE_") || k === "PYTHONIOENCODING";
}

function run(kind, row) {
  const c = expandRepeat(row);
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
  it("repeat expands a declared token, and refuses one used but not declared or declared but not used", () => {
    const row = { name: "x", expectExit: 0, repeat: { LONG: ["ab", 3] }, cfg: { layers: ["{{LONG}}"] }, expectStderr: "{{LONG}}!" };
    expect(typeProblems(row)).toEqual([]);
    expect(expandRepeat(row).cfg.layers).toEqual(["ababab"]);
    expect(expandRepeat(row).expectStderr).toBe("ababab!");
    expect(typeProblems({ name: "x", expectExit: 0, stdin: "{{LONG}}" })).toEqual(["repeat token {{LONG}} is not declared"]);
    expect(typeProblems({ name: "x", expectExit: 0, repeat: { LONG: ["a", 2] } })).toEqual(["repeat.LONG is not used"]);
    expect(typeProblems({ name: "x", expectExit: 0, repeat: { LONG: ["a", 0] }, stdin: "{{LONG}}" }))
      .toEqual(["repeat.LONG must be [a non-empty string, a count from 1 to 1000000]"]);
    expect(typeProblems({ name: "x", expectExit: 0, repeat: { long: ["a", 2] }, stdin: "{{long}}" }))
      .toEqual(["repeat key \"long\" must be an upper-case name",
        "a repeat token must be written {{UPPER_CASE}}", "repeat.long is not used"]);
  });
  it("repeat accepts a whole float count and refuses keys, malformed tokens and long expansions (#513 review)", () => {
    expect(typeProblems(JSON.parse('{"name": "x", "expectExit": 0, "repeat": {"A": ["a", 2.0]}, "stdin": "{{A}}"}'))).toEqual([]);
    expect(typeProblems({ name: "x", expectExit: 0, cfg: { "{{A}}": "x" } }))
      .toEqual(["repeat tokens are expanded only in values, not keys"]);
    expect(typeProblems({ name: "x", expectExit: 0, stdin: "{{long}}" }))
      .toEqual(["a repeat token must be written {{UPPER_CASE}}"]);
    expect(typeProblems({ name: "x", expectExit: 0, repeat: { A: ["ab", 60000] }, stdin: "{{A}}" }))
      .toEqual(["repeat.A must expand to at most 100000 characters"]);
    expect(typeProblems({ name: "x", expectExit: 0, repeat: { B: ["a", 1], 10: ["a", 1] }, stdin: "{{B}}" }))
      .toEqual(["repeat key \"10\" must be an upper-case name", "repeat.10 is not used"]);
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
  // Judged as the row runs: after any repeat is expanded (#513 review).
  const read = (cases.branchGuard ?? []).map((c) => [c, readsBranch(expandRepeat(c))]).filter(([, r]) => r);
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
        const ex = expandRepeat(c);
        expect(r.error, "the hook did not start, or timed out").toBeUndefined();
        expect(r.status, r.stderr).toBe(c.expectExit);
        if (ex.expectStderr !== undefined) expect(r.stderr).toContain(ex.expectStderr);
      });
    }
  });
}
