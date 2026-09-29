// vitest.test.mjs — the fixture quarantine for vitest (#123). Owner decisions
// on #123: marking is opt-in per fixture (markFixture); the no-taint check
// takes a marked value only (#544 assesses walking a structure). The check is
// guard (#120) with its defaults. Python twin: tests/test_pytest_plugin.py.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
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

describe("the helper stays dependency-free", () => {
  it("never imports vitest: the user registers the matchers", () => {
    const src = readFileSync(fileURLToPath(new URL("./vitest.mjs", import.meta.url)), "utf8");
    expect(src).not.toMatch(/from\s+["']vitest["']/);
  });

  it("is published on the ./vitest subpath", () => {
    const pkg = JSON.parse(readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf8"));
    expect(pkg.exports["./vitest"]).toBe("./vitest.mjs");
    expect(pkg.files).toContain("vitest.mjs");
  });
});
