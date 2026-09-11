import { describe, it, expect, afterAll, beforeAll, vi } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { mark, derive } from "./marked.mjs";
import { update } from "./baseline.mjs";
import { main } from "./baseline-cli.mjs";

const CLI = fileURLToPath(new URL("./baseline-cli.mjs", import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "plumb-baseline-cli-"));
const dirDirect = mkdtempSync(join(tmpdir(), "plumb-baseline-direct-"));
afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
  rmSync(dirDirect, { recursive: true, force: true });
});
const run = (...args) => {
  const p = spawnSync(process.execPath, [CLI, ...args], { encoding: "utf8" });
  return { code: p.status, out: p.stdout + p.stderr };
};

beforeAll(() => {
  const r = mark(0.04, { source: "real", confidence: "high" });
  update("nightly-rate", derive([r], (x) => x * 2), { because: "initial pin", dir, date: "2026-09-10" });
});

describe("baseline-cli", () => {
  it("list prints names and the denominator", () => {
    const { code, out } = run("list", "--dir", dir);
    expect(code).toBe(0);
    expect(out).toContain("nightly-rate");
    expect(out).toMatch(/1 baseline\(s\) in /);
  });
  it("list on a missing directory says so and exits 0", () => {
    const { code, out } = run("list", "--dir", join(dir, "absent"));
    expect(code).toBe(0);
    expect(out).toContain("no baselines directory at");
  });
  it("show prints the trust state and the history", () => {
    const { code, out } = run("show", "nightly-rate", "--dir", dir);
    expect(code).toBe(0);
    expect(out).toContain('source: "derived"');
    expect(out).toContain("2026-09-10  initial  initial pin");
  });
  it("show on an unknown name exits 1", () => {
    expect(run("show", "nope", "--dir", dir).code).toBe(1);
  });
  it("validate passes clean files and names broken ones", () => {
    expect(run("validate", "--dir", dir).code).toBe(0);
    writeFileSync(join(dir, "broken.json"), "{ not json");
    const { code, out } = run("validate", "--dir", dir);
    expect(code).toBe(1);
    expect(out).toContain("broken.json");
    expect(out).toMatch(/1 of 2 invalid/);
    expect(out.indexOf("broken.json") < out.indexOf("nightly-rate.json")).toBe(true);
  });
  it("list on a path that is a regular file says so and exits 0, as Python does", () => {
    const { code, out } = run("list", "--dir", join(dir, "nightly-rate.json"));
    expect(code).toBe(0);
    expect(out).toContain("no baselines directory at");
  });
  it("validate on a path that is a regular file states the 0 denominator and exits 0", () => {
    const { code, out } = run("validate", "--dir", join(dir, "nightly-rate.json"));
    expect(code).toBe(0);
    expect(out).toContain("; 0 files validated");
  });
  it("--dir with no value is a usage error, never a silent fallback to the default", () => {
    const { code, out } = run("list", "--dir");
    expect(code).toBe(2);
    expect(out).toContain("usage: baseline <list|show <name>|validate> [--dir D]");
  });
  it("an unknown subcommand prints the literal usage line and exits 2", () => {
    const { code, out } = run("bogus");
    expect(code).toBe(2);
    expect(out).toContain("usage: baseline <list|show <name>|validate> [--dir D]");
  });
  it("validate reports a record whose name does not match its filename", () => {
    const odd = mkdtempSync(join(tmpdir(), "plumb-baseline-name-"));
    update("nightly-rate", derive([mark(0.04, { source: "real", confidence: "high" })], (x) => x * 2),
           { because: "initial pin", dir: odd, date: "2026-09-10" });
    copyFileSync(join(odd, "nightly-rate.json"), join(odd, "other-name.json"));
    const { code, out } = run("validate", "--dir", odd);
    expect(code).toBe(1);
    expect(out).toContain("\u2717 other-name.json");
    expect(out).toContain("does not match the filename");
    rmSync(odd, { recursive: true, force: true });
  });
  it("usage on no subcommand exits 2", () => {
    const { code, out } = run();
    expect(code).toBe(2);
    expect(out).toContain('usage: baseline <list|show <name>|validate> [--dir D]');
  });
});

describe("baseline-cli direct", () => {
  beforeAll(() => {
    const r = mark(0.04, { source: "real", confidence: "high" });
    update("nightly-rate", derive([r], (x) => x * 2), { because: "initial pin", dir: dirDirect, date: "2026-09-10" });
  });

  it("show with no name returns 2", () => {
    let errorMsg = "";
    const err = vi.spyOn(console, "error").mockImplementation((msg) => {
      errorMsg = msg;
    });
    expect(main(["show", "--dir", dirDirect])).toBe(2);
    expect(errorMsg).toBe("usage: baseline show <name> [--dir D]");
    err.mockRestore();
  });
  it("list command via direct call", () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["list", "--dir", dirDirect])).toBe(0);
    log.mockRestore();
  });
  it("show command via direct call", () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["show", "nightly-rate", "--dir", dirDirect])).toBe(0);
    log.mockRestore();
  });
  it("validate command via direct call", () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["validate", "--dir", dirDirect])).toBe(0);
    log.mockRestore();
  });
  it("validate on a missing directory exits 0 with note", () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["validate", "--dir", join(dirDirect, "nonexistent")])).toBe(0);
    log.mockRestore();
  });
  it("validate with no files in empty directory", () => {
    const emptyDir = mkdtempSync(join(tmpdir(), "plumb-baseline-empty-"));
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["validate", "--dir", emptyDir])).toBe(0);
    log.mockRestore();
    rmSync(emptyDir, { recursive: true, force: true });
  });
  it("invalid subcommand returns 2", () => {
    let errorMsg = "";
    const err = vi.spyOn(console, "error").mockImplementation((msg) => {
      errorMsg = msg;
    });
    expect(main(["invalid"])).toBe(2);
    expect(errorMsg).toBe('usage: baseline <list|show <name>|validate> [--dir D]');
    err.mockRestore();
  });
  it("validate with invalid JSON file returns 1", () => {
    const broken = mkdtempSync(join(tmpdir(), "plumb-baseline-broken-"));
    writeFileSync(join(broken, "bad.json"), "{ not json");
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    expect(main(["validate", "--dir", broken])).toBe(1);
    log.mockRestore();
    rmSync(broken, { recursive: true, force: true });
  });
});
