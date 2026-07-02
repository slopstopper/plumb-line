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

  it("allows the commit when there are no runners", async () => {
    const r = await decide({ runners: [] });
    expect(r.allow).toBe(true);
  });
});
