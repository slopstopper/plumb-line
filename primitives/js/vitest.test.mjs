// vitest.test.mjs — the fixture quarantine for vitest (#123). Owner decisions
// on #123: marking is opt-in per fixture (markFixture); the no-taint check
// takes a marked value only (#544 assesses walking a structure). The check is
// guard (#120) with its defaults. Python twin: tests/test_pytest_plugin.py.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import * as nodeModule from "node:module"; // a namespace: a named import of a missing export fails to link
import { appendFileSync, copyFileSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { markFixture, assertNoTaint, assertTainted, plumbMatchers } from "./vitest.mjs";
import { mark, derive, metaOf, unwrap } from "./index.mjs";

expect.extend(plumbMatchers);

const clean = () => mark(1, { source: "real", confidence: "high" });
const fromFixture = () =>
  derive([mark(100, { source: "real", confidence: "high" }), markFixture(1.17)], (a, r) => a * r);

describe("markFixture — opt-in per fixture (#123)", () => {
  it("marks a fixture value mock", () => {
    const rate = markFixture(1.17);
    expect(unwrap(rate)).toBe(1.17);
    expect(metaOf(rate).source).toBe("mock");
    expect(metaOf(rate).derivedFromMock).toBe(true);
  });

  it.each([
    [{ value: 42, label: "x" }],
    [{ value: 3, meta: { page: 1 } }],
    [new (class Box { constructor() { this.value = 1; } })()],
    [{ value: 1, meta: "not an envelope" }],
  ])("marks ordinary fixture data shaped like a marked value, rather than refuse it (%#)", (data) => {
    const marked = markFixture(data);
    expect(unwrap(marked)).toBe(data);
    expect(metaOf(marked).source).toBe("mock");
  });

  it("reads the value's own fields only, as guard does, so a polluted prototype cannot make data look marked", () => {
    const fields = { source: "real", confidence: "high", derivedFromMock: false, lineage: [] };
    try {
      Object.assign(Object.prototype, fields);
      expect(metaOf(markFixture({ value: 1 })).source).toBe("mock");
    } finally {
      for (const k of Object.keys(fields)) delete Object.prototype[k];
    }
  });

  it("refuses a value that is already marked, rather than nest or relabel it", () => {
    expect(() => markFixture(clean())).toThrow(/markFixture: the fixture returned a marked value/);
    expect(() => markFixture(clean())).toThrow(TypeError);
  });
});

describe("assertNoTaint — guard's no-mock check as a test assertion (#123)", () => {
  it("passes a clean value and returns nothing", () => {
    expect(assertNoTaint(clean())).toBeUndefined();
  });

  it("fails a value derived from a fixture, with guard's reasons, the same message as Python", () => {
    expect(() => assertNoTaint(fromFixture())).toThrow(
      /^no mock taint may reach a golden output: provenance refused: .*mock:/);
  });

  it("fails an unmarked value", () => {
    expect(() => assertNoTaint(42)).toThrow(/not a marked value/);
  });
});

describe("toBeUntainted — the same check as a matcher registered with expect.extend", () => {
  it("passes a clean value, and its negation passes a tainted one", () => {
    expect(clean()).toBeUntainted();
    expect(fromFixture()).not.toBeUntainted();
  });

  it("fails with guard's reasons", () => {
    expect(() => expect(fromFixture()).toBeUntainted()).toThrow(/provenance refused: .*mock:/);
    expect(() => expect(clean()).not.toBeUntainted()).toThrow(/guard let it through/);
  });

  it("negated, passes only for mock taint: a value guard refuses for another reason is not proof", () => {
    for (const other of [42, undefined, { value: 1 }]) {
      expect(() => expect(other).not.toBeUntainted()).toThrow(/guard refused it, but not for mock taint/);
    }
  });
});

describe("assertTainted — the positive claim, verified (twin: assert_tainted)", () => {
  it("passes only when guard refuses for mock taint", () => {
    expect(assertTainted(fromFixture())).toBeUndefined();
  });

  it("fails a value guard refuses for another reason, and a clean one, with Python's wording", () => {
    for (const other of [42, null, { value: 1, source: "real" }]) {
      expect(() => assertTainted(other)).toThrow(
        /^mock taint was expected to reach this value: guard refused it, but not for mock taint/);
    }
    expect(() => assertTainted(clean())).toThrow(/^mock taint was expected to reach this value: guard let it through/);
  });
});

// Loads a module in a child Node process whose resolver refuses `vitest`
// (and `vitest/*`, `@vitest/*`), and records every attempt to resolve it,
// as the Python twin makes `pytest` unimportable (#597). The hook is
// synchronous (module.registerHooks, Node >= 22.15), so an import("vitest")
// made while the module loads, or while the child runs each export once, is
// recorded at the call, even when the module swallows the rejection. It is
// not exhaustive: a path the child does not run is not checked. `probe` is
// the child's own import("vitest") afterwards: refused by the hook, and
// recorded, it shows the hook was live, so an empty record is not vacuous;
// vitest resolves from this directory without it.
const CHILD = `
import { registerHooks } from "node:module";
if (typeof registerHooks !== "function")
  throw new Error("this check needs module.registerHooks (Node >= 22.15)");
const attempts = [];
registerHooks({
  resolve(specifier, context, next) {
    if (/^(vitest|@vitest\\/[^/]+)(\\/|$)/.test(specifier)) {
      attempts.push(specifier);
      throw new Error("refused: " + specifier);
    }
    return next(specifier, context);
  },
});
let loaded = "loaded", exports = [];
try {
  const m = await import(process.env.PLUMB_TARGET);
  exports = Object.keys(m).sort();
  // Run each export once too, so an import("vitest") made on first use is recorded.
  const tainted = m.markFixture(1);
  m.assertTainted(tainted);
  try { m.assertNoTaint(tainted); } catch { /* expected: tainted */ }
  m.plumbMatchers.toBeUntainted.call({ isNot: false }, tainted);
  m.plumbMatchers.toBeUntainted.call({ isNot: true }, tainted);
  for (let i = 0; i < 3; i++) await new Promise((r) => setImmediate(r));
} catch (e) { loaded = String(e); }
const asked = [...attempts];
const probe = await import("vitest").then(() => "resolved", (e) => String(e.message));
const probeRecorded = attempts.length === asked.length + 1;
process.stdout.write(JSON.stringify({ loaded, exports, asked, probe, probeRecorded }));
`;

function loadWithVitestUnresolvable(url) {
  const p = spawnSync(process.execPath, ["--input-type=module", "-e", CHILD], {
    encoding: "utf8",
    cwd: fileURLToPath(new URL(".", import.meta.url)), // where the probe's vitest would resolve
    env: { ...process.env, PLUMB_TARGET: url.href },
  });
  expect(p.status, p.stderr).toBe(0);
  return JSON.parse(p.stdout);
}

// The shipped modules, copied to a temporary directory with `line` added to
// vitest.mjs: a planted wrong version of the helper.
function plantedHelper(line) {
  const pkg = JSON.parse(readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf8"));
  const dir = mkdtempSync(join(tmpdir(), "plumb-vitest-plant-"));
  for (const f of pkg.files.filter((f) => f.endsWith(".mjs")))
    copyFileSync(fileURLToPath(new URL(`./${f}`, import.meta.url)), join(dir, f));
  appendFileSync(join(dir, "vitest.mjs"), `\n${line}\n`);
  return { url: pathToFileURL(join(dir, "vitest.mjs")), dir };
}

// The engines floor is Node >= 22, but the child's hook needs
// module.registerHooks (Node >= 22.15). Below that these tests skip, with the
// reason in their title, rather than fail a contributor's change for a reason
// unrelated to it. Not in CI: there a skip would be a lost proof (ADR-0016),
// so CI runs them, and they fail if its Node is too old.
const NO_REGISTER_HOOKS = typeof nodeModule.registerHooks !== "function" && !process.env.CI;

describe("the helper stays dependency-free", () => {
  describe.skipIf(NO_REGISTER_HOOKS)(NO_REGISTER_HOOKS
    ? `with vitest unresolvable: SKIPPED, needs module.registerHooks (Node >= 22.15); this is Node ${process.versions.node}`
    : "with vitest unresolvable", () => {
    it("never imports vitest: it loads and runs where vitest cannot be resolved, asking for it neither at load nor on use", () => {
      const r = loadWithVitestUnresolvable(new URL("./vitest.mjs", import.meta.url));
      expect(r.probe).toBe("refused: vitest");
      expect(r.probeRecorded).toBe(true);
      expect(r.asked).toEqual([]);
      expect(r.loaded).toBe("loaded");
      expect(r.exports).toEqual(expect.arrayContaining(["assertNoTaint", "assertTainted", "markFixture", "plumbMatchers"]));
    });

    it.each([
      ["a named import", 'import { expect } from "vitest";'],
      ["a side-effect import", 'import "vitest";'],
      ["a subpath import", 'import "vitest/config";'],
      ["a dynamic import at load time, its failure swallowed", 'void import("vitest").catch(() => {});'],
      ["a dynamic import on first use of a matcher", [
        "const _plain = plumbMatchers.toBeUntainted;",
        'plumbMatchers.toBeUntainted = function (...a) { void import("vitest").catch(() => {}); return _plain.apply(this, a); };',
      ].join("\n")],
    ])("catches a planted helper that imports vitest through %s", (_how, line) => {
      const { url, dir } = plantedHelper(line);
      try {
        expect(loadWithVitestUnresolvable(url).asked).not.toEqual([]);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });
  });

  it("is published on the ./vitest subpath", () => {
    const pkg = JSON.parse(readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf8"));
    expect(pkg.exports["./vitest"]).toBe("./vitest.mjs");
    expect(pkg.files).toContain("vitest.mjs");
  });
});
