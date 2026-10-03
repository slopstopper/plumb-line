import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { classifyBranch, decide, splitCommand } from "../pre-commit-gate.mjs";
import {
  decide as guardDecide, ignoreCaseFrom, isBranchName, isCaseAlias, protectedMatch, readIgnoreCase,
} from "../branch-guard.mjs";

/**
 * Deterministic random strings over the characters the splitter treats
 * specially, plus a non-BMP character and lone surrogates (#472 review).
 * Seeded, so a failure names the same string on every run.
 */
function seededStrings(n) {
  const alphabet = [" ", "\t", "\r", "\n", "'", "\"", "\\", "#", "a", "-", "é", "$", "😀",
    "\ud800", "\udc00", " ", "　"];
  let seed = 472;
  const next = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
  return Array.from({ length: n }, () =>
    Array.from({ length: 1 + Math.floor(next() * 12) }, () => alphabet[Math.floor(next() * alphabet.length)]).join(""));
}

// #472: the reference for splitting PLUMBLINE_TEST_CMD is the Python twin's
// shlex.split. Every command in the shared table, and a few harder strings,
// must split the same way here, or fail with the same message.
describe("splitCommand agrees with Python's shlex.split (#472)", () => {
  const table = JSON.parse(readFileSync(
    fileURLToPath(new URL("../../../hook-cases.json", import.meta.url)), "utf8"));
  const commands = [
    ...table.preCommitGate.map((c) => c.env?.PLUMBLINE_TEST_CMD).filter((c) => typeof c === "string"),
    "", "a  b", " lead", "trail ", "a\\", "\"a\\", "'a\\'", "a'b'c", "a\"b\"c", "\"\"", "''x", "a\\\\b",
    "\"a\\\\b\"", "\"a\\$b\"", "a\\'b", "'a\"b'", "\"a'b\"", "x\\\ny", "é 'ü'", "a\r\nb",
    ...seededStrings(300),
  ];
  const py = spawnSync("python3", ["-c", [
    "import json, shlex, sys",
    "out = []",
    "for c in json.load(sys.stdin):",
    "    try: out.append(shlex.split(c))",
    "    except ValueError as e: out.append(str(e))",
    "print(json.dumps(out))",
  ].join("\n")], { input: JSON.stringify(commands), encoding: "utf8" });

  it("Python ran", () => {
    expect(py.error, "python3 did not start").toBeUndefined();
    expect(py.status, py.stderr).toBe(0);
  });
  const expected = py.status === 0 ? JSON.parse(py.stdout) : [];
  commands.forEach((cmd, i) => {
    it(JSON.stringify(cmd), () => {
      let got;
      try {
        got = splitCommand(cmd);
      } catch (e) {
        got = e.message;
      }
      expect(got).toEqual(expected[i]);
    });
  });
});

describe("pre-commit-gate decide", () => {
  it("allows the commit when every runner passes", async () => {
    const r = await decide({
      runners: [
        { name: "tests", fn: () => true },
        { name: "lint", fn: async () => true },
      ],
    });
    expect(r.allow).toBe(true);
    expect(r.reason).toMatch(/all gates passed/i);
  });

  it("blocks the commit and names the first failing runner", async () => {
    const calls = [];
    const r = await decide({
      runners: [
        { name: "tests", fn: () => { calls.push("tests"); return false; } },
        { name: "lint", fn: () => { calls.push("lint"); return true; } },
      ],
    });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/pre-commit blocked: tests failed/);
    // short-circuits: the runner after the first failure never runs.
    expect(calls).toEqual(["tests"]);
  });

  // #476: a gate that ran nothing must not report that everything passed.
  // Every way of not running the tests blocks (#467), in both twins.
  it("blocks the commit when there are no runners, with its own reason", async () => {
    const r = await decide({ runners: [] });
    expect(r).toEqual({ allow: false, reason: "pre-commit blocked: no gates configured" });
  });

  it("reads a generator of runners lazily, stopping at the first failure", async () => {
    const order = [];
    function* runners() {
      order.push("y1");
      yield { name: "tests", fn: () => { order.push("tests"); return false; } };
      order.push("y2");
      yield { name: "lint", fn: () => true };
    }
    const r = await decide({ runners: runners() });
    expect(r.allow).toBe(false);
    expect(order).toEqual(["y1", "tests"]);
  });

  it("blocks when the runners are an empty iterable with no length", async () => {
    const r = await decide({ runners: (function* () {})() });
    expect(r).toEqual({ allow: false, reason: "pre-commit blocked: no gates configured" });
  });

  // #493 (owner decision): a runner passes only by returning true. Anything
  // else that is not false is an answer the gate cannot read, so it blocks,
  // with the same reason as the Python twin.
  for (const [label, value] of [["1", 1], ["\"ok\"", "ok"], ["undefined", undefined], ["null", null], ["an object", {}]]) {
    it(`blocks when a runner returns ${label}, which is not true or false`, async () => {
      const r = await decide({ runners: [{ name: "tests", fn: () => value }] });
      expect(r).toEqual({
        allow: false,
        reason: "pre-commit blocked: tests returned a result that is not true or false",
      });
    });
  }

  it("awaits an async runner, so one that resolves to true passes", async () => {
    const r = await decide({ runners: [{ name: "tests", fn: async () => true }] });
    expect(r.allow).toBe(true);
  });

  it("blocks an async runner that resolves to something other than true or false", async () => {
    const r = await decide({ runners: [{ name: "tests", fn: async () => 1 }] });
    expect(r.reason).toBe("pre-commit blocked: tests returned a result that is not true or false");
  });
});

// CLI behaviour is in adapters/hook-cases.json, run against both twins by
// hook-cases.test.mjs (#475).

// #613: the branch-aware gate. Its CLI is in adapters/commit-hook-cases.json;
// these pin classifyBranch() in-process, and the case helpers it shares with
// the branch guard (#615). Python twin: test_hooks.py.
describe("classifyBranch (#613)", () => {
  const classify = (resolved, protectedBranches = ["main"], ignoreCase = false) =>
    classifyBranch({ resolved, isBranchName, protectedName: (b) => protectedMatch(b, protectedBranches, ignoreCase) });
  it("reads the branch and every branch a rebase moves", () => {
    expect(classify({ branch: "feat" })).toEqual({ kind: "other", branch: "feat" });
    expect(classify({ branch: "main" })).toEqual({ kind: "protected", branch: "main" });
    expect(classify({ branch: "feat", also: ["other", "main"] })).toEqual({ kind: "protected", branch: "main" });
    expect(classify({ branch: "feat", also: ["other"] })).toEqual({ kind: "other", branch: "feat" });
  });
  it("treats every unreadable branch as unknown", () => {
    expect(classify({ branch: null })).toEqual({ kind: "unknown", why: "HEAD is not on a branch" });
    expect(classify({ branch: "-x" })).toEqual({ kind: "unknown", why: 'HEAD is on "-x", which is not a branch name' });
    expect(classify({ branch: "feat", why: "a reason" })).toEqual({ kind: "unknown", why: "a reason" });
    expect(classify({ branch: "feat", alsoWhy: "unread" })).toEqual({ kind: "unknown", why: "unread" });
    expect(classify({ branch: "feat", also: ["-y"] }))
      .toEqual({ kind: "unknown", why: 'the rebase also moves "-y", which is not a branch name' });
    // Unknown is never a pass, even with no branch protected.
    expect(classify({ branch: null }, [])).toEqual({ kind: "unknown", why: "HEAD is not on a branch" });
  });
  it("judges the branch before the ones a rebase moves", () => {
    // As the commit hook does: a protected branch is named before an
    // update-refs that cannot be read.
    expect(classify({ branch: "main", alsoWhy: "unread" })).toEqual({ kind: "protected", branch: "main" });
  });
});

describe("case aliases of a protected branch (#615)", () => {
  const classify = (resolved, ignoreCase = false) =>
    classifyBranch({ resolved, isBranchName, protectedName: (b) => protectedMatch(b, ["main"], ignoreCase) });
  it("classifyBranch matches a case alias only where git ignores case", () => {
    // The protected name is the one reported.
    expect(classify({ branch: "Main" })).toEqual({ kind: "other", branch: "Main" });
    expect(classify({ branch: "Main" }, true)).toEqual({ kind: "protected", branch: "main" });
    expect(classify({ branch: "feat", also: ["MAIN"] }, true)).toEqual({ kind: "protected", branch: "main" });
  });
  it("protectedMatch and isCaseAlias", () => {
    expect(protectedMatch("main", ["main"])).toBe("main");
    expect(protectedMatch("Main", ["main"])).toBeNull();
    expect(protectedMatch("Main", ["main"], true)).toBe("main");
    expect(protectedMatch("feat", ["main"], true)).toBeNull();
    // Upper then lower: U+017F long s folds to s, as APFS reads it (#615 review).
    expect(protectedMatch("maſter", ["master"], true)).toBe("master");
    expect(isCaseAlias("maſter", ["master"])).toBe(true);
    expect(isCaseAlias("Main", ["main"])).toBe(true);
    expect(isCaseAlias("main", ["main"])).toBe(false);
    expect(isCaseAlias("feat", ["main"])).toBe(false);
  });
  it("normalizes both names to NFC before folding, only where case is ignored (#625)", () => {
    // é precomposed (U+00E9) and e + U+0301 are one name to APFS.
    expect(protectedMatch("café", ["café"], true)).toBe("café");
    expect(protectedMatch("CAFÉ", ["café"], true)).toBe("café");
    expect(protectedMatch("café", ["café"], true)).toBe("café");
    expect(protectedMatch("café", ["café"])).toBeNull();
    expect(isCaseAlias("café", ["café"])).toBe(true);
    // ASCII is unchanged.
    expect(protectedMatch("MAIN", ["main"], true)).toBe("main");
    expect(protectedMatch("feat", ["main"], true)).toBeNull();
  });
  it("fails closed on a character the runtime does not know, only where case is ignored (#625)", () => {
    // U+40000 is unassigned (Cn) in Unicode 17; if a later Unicode assigns
    // it, this row needs another unassigned code point.
    expect(/\p{Cn}/u.test("\u{40000}")).toBe(true);
    expect(protectedMatch("x\u{40000}", ["main", "release"], true)).toBe("main");
    expect(protectedMatch("x\u{40000}", ["main"])).toBeNull();
    expect(isCaseAlias("x\u{40000}", ["main"])).toBe(true);
    // A real fold match is named over the first protected branch.
    expect(protectedMatch("X\u{40000}", ["main", "x\u{40000}"], true)).toBe("x\u{40000}");
    // With no branch protected, there is nothing for it to be.
    expect(protectedMatch("x\u{40000}", [], true)).toBeNull();
    // The pair that split the twins: folded where U+A7CE is known, and
    // protected by the rule above where it is not.
    expect(protectedMatch("x꟎", ["x꟏"], true)).toBe("x꟏");
  });
  for (const [status, stdout, expected] of [
    [0, "true\n", true], [0, "false\n", false], [1, "", false],
    // Anything else cannot be read: fail closed, including exit 0 with output
    // other than true or false (v0.12.0 dogfood of #617).
    [128, "", true], [0, "yes\n", true], [0, "", true], [2, "", true],
    // Only ASCII whitespace is trimmed, as in the Python twin.
    [0, "﻿false\n", true], [0, "false \n", true], [0, "false\r\n", false],
  ]) {
    it(`ignoreCaseFrom(${status}, ${JSON.stringify(stdout)}) is ${expected}`, () => {
      expect(ignoreCaseFrom(status, stdout)).toBe(expected);
    });
  }
  it("readIgnoreCase fails closed outside a repository", () => {
    expect(readIgnoreCase(path.join(os.tmpdir(), "plumb-line-615-missing"))).toBe(true);
  });
  it("the branch guard's decide takes ignoreCase", () => {
    expect(guardDecide({ filePath: "src/a.py", branch: "Main", protectedBranches: ["main"], ignoreCase: true }))
      .toEqual({ allow: false, reason: "blocked: code edit to src/a.py on protected branch main. Branch first." });
    expect(guardDecide({ filePath: "src/a.py", branch: "Main", protectedBranches: ["main"] }).allow).toBe(true);
  });
});
