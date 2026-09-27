import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { decide, splitCommand } from "../pre-commit-gate.mjs";

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
});

// CLI behaviour is in adapters/hook-cases.json, run against both twins by
// hook-cases.test.mjs (#475).
