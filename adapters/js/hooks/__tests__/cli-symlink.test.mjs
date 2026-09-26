// cli-symlink.test.mjs — every JS hook's CLI runs when invoked through a
// symlink (v0.11.3 dogfood finding). boundary-guard and pre-commit-gate
// compared `import.meta.url` to `file://${process.argv[1]}` as strings, so a
// hook linked into .git/hooks or a tool directory never ran its body and
// exited 0 — a guard that silently allowed everything. branch-guard already
// resolved both sides with realpath; the other two now share that check.
import { describe, it, expect, afterAll } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, symlinkSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const hooks = join(dirname(fileURLToPath(import.meta.url)), "..");
const tmp = mkdtempSync(join(tmpdir(), "plumb-hook-link-"));
afterAll(() => rmSync(tmp, { recursive: true, force: true }));

function linked(name) {
  const link = join(tmp, name);
  symlinkSync(join(hooks, name), link);
  return link;
}

function run(script, { input = "", env = {} } = {}) {
  const e = { ...process.env, ...env };
  delete e.PLUMBLINE_TEST_CMD;
  Object.assign(e, env);
  return spawnSync(process.execPath, [script], { input, env: e, encoding: "utf8" });
}

const upward = {
  input: JSON.stringify({ filePath: "src/data/a.js", importPath: "src/ui/b.js" }),
  env: { PLUMBLINE_CFG: JSON.stringify({ layers: ["ui", "services", "engine", "data"] }) },
};

describe("hook CLIs run when invoked through a symlink", () => {
  it("boundary-guard blocks an upward import, direct and linked", () => {
    expect(run(join(hooks, "boundary-guard.mjs"), upward).status).toBe(2);
    expect(run(linked("boundary-guard.mjs"), upward).status).toBe(2);
  });

  it("pre-commit-gate blocks when PLUMBLINE_TEST_CMD is unset, direct and linked", () => {
    expect(run(join(hooks, "pre-commit-gate.mjs")).status).toBe(2);
    expect(run(linked("pre-commit-gate.mjs")).status).toBe(2);
  });

  it("branch-guard blocks a code edit on main, direct and linked", () => {
    const opts = { input: JSON.stringify({ filePath: "src/app.js" }), env: { PLUMBLINE_BRANCH: "main" } };
    expect(run(join(hooks, "branch-guard.mjs"), opts).status).toBe(2);
    expect(run(linked("branch-guard.mjs"), opts).status).toBe(2);
  });
});
