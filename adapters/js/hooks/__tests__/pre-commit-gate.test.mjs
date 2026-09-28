import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { decide, splitCommand } from "../pre-commit-gate.mjs";

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
