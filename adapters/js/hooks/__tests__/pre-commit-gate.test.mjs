import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
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

// #467: a Claude Code hook treats only exit 2 as a block; exit 1 lets the
// action through. Every way the gate cannot run the tests must exit 2.
describe("pre-commit-gate CLI", () => {
  const gatePath = fileURLToPath(new URL("../pre-commit-gate.mjs", import.meta.url));
  function runGate(cmd) {
    const env = { ...process.env };
    delete env.PLUMBLINE_TEST_CMD;
    if (cmd !== null) env.PLUMBLINE_TEST_CMD = cmd; // null = unset
    return spawnSync("node", [gatePath], { encoding: "utf8", env });
  }

  it("exits 2 when PLUMBLINE_TEST_CMD is unset", () => {
    const r = runGate(null);
    expect(r.status).toBe(2);
    expect(r.stderr).toMatch(/PLUMBLINE_TEST_CMD/);
  });

  it("exits 2 when PLUMBLINE_TEST_CMD is blank", () => {
    expect(runGate("   ").status).toBe(2);
  });

  it("exits 2 when the command cannot be started", () => {
    expect(runGate("plumb-line-no-such-command-467").status).toBe(2);
  });

  it("exits 2 when the command fails", () => {
    expect(runGate("node -e process.exit(3)").status).toBe(2);
  });

  it("exits 0 when the command passes", () => {
    expect(runGate("node -e process.exit(0)").status).toBe(0);
  });
});
