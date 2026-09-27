import { describe, it, expect } from "vitest";
import { decide } from "../pre-commit-gate.mjs";

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
