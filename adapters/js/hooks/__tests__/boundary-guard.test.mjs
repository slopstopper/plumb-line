import { describe, it, expect } from "vitest";
import { decide } from "../boundary-guard.mjs";

// layers ordered top->bottom; imports may only go downward (top imports lower).
const cfg = {
  layers: ["ui", "engine", "services", "data"],
  direction: "downward",
};

describe("boundary-guard decide", () => {
  it("blocks a lower layer importing an upper layer", () => {
    const r = decide({
      filePath: "src/data/store.js",
      importPath: "../ui/button.js",
      ...cfg,
    });
    expect(r.allow).toBe(false);
  });
  it("allows an upper layer importing a lower layer", () => {
    const r = decide({
      filePath: "src/ui/button.js",
      importPath: "../engine/calc.js",
      ...cfg,
    });
    expect(r.allow).toBe(true);
  });
  it("allows same-layer imports", () => {
    const r = decide({
      filePath: "src/engine/a.js",
      importPath: "../engine/b.js",
      ...cfg,
    });
    expect(r.allow).toBe(true);
  });

  it("matches layer names with regex metacharacters literally, not as wildcards", () => {
    // Layer "a.b" must not match "axb" — the dot must be treated as a literal character.
    const metaCfg = { layers: ["a.b", "engine"], direction: "downward" };
    const noMatch = decide({
      filePath: "src/axb/thing.js",
      importPath: "src/engine/calc.js",
      ...metaCfg,
    });
    // "axb" does not contain the literal layer "a.b", so filePath is unscoped → allow
    expect(noMatch.allow).toBe(true);
    expect(noMatch.reason).toBe("same or unscoped layer");

    const exactMatch = decide({
      filePath: "src/a.b/thing.js",
      importPath: "src/engine/calc.js",
      ...metaCfg,
    });
    // "a.b" is the top layer (index 0), "engine" is index 1 → downward → allow
    expect(exactMatch.allow).toBe(true);
    expect(exactMatch.reason).toMatch(/respects downward/);
  });

  // #471: the CLI rows in adapters/hook-cases.json pin the same rules end to
  // end; these pin decide() for a caller that imports it. Python twin:
  // test_boundary_decide_* in adapters/python/hooks/test_hooks.py.
  it.each([undefined, null, "", 7])("blocks with no file path to judge (%s)", (filePath) => {
    const r = decide({ filePath, importPath: "src/ui/button.js", ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/^blocked: no file path to judge\./);
  });
  it.each([undefined, null, ""])("allows a file path with no import to judge (%s)", (importPath) => {
    const r = decide({ filePath: "src/data/store.js", importPath, ...cfg });
    expect(r).toEqual({ allow: true, reason: "no import to judge" });
  });
  it("blocks an importPath that is not a string", () => {
    const r = decide({ filePath: "src/data/store.js", importPath: 7, ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/^blocked: importPath must be a string\./);
  });

  // #516: an import to judge with no layers blocks, for a caller of decide()
  // as for the CLI. Python twin: the #516 tests in test_hooks.py.
  it.each([undefined, null, []])("blocks an import with no layers configured (%s)", (layers) => {
    const r = decide({ filePath: "src/data/store.js", importPath: "src/ui/button.js", layers });
    expect(r).toEqual({
      allow: false,
      reason:
        'blocked: no layers configured, so this import cannot be judged. Set "layers" in ' +
        "PLUMBLINE_CFG to the project's layer names, top to bottom.",
    });
  });
  it.each(["ui", 7, { ui: 1 }, [1], ["ui", ""], ["ui", null]])("blocks layers that are not a list of layer names, with its own reason (%j)", (layers) => {
    const r = decide({ filePath: "src/data/store.js", importPath: "src/ui/button.js", layers });
    expect(r).toEqual({ allow: false, reason: "blocked: layers must be a list of layer names." });
  });
  it("with no layers, the earlier checks keep their order and reasons", () => {
    const base = { importPath: "src/ui/button.js", layers: [] };
    expect(decide({ ...base, filePath: "" }).reason).toMatch(/^blocked: no file path to judge\./);
    expect(decide({ ...base, filePath: "src/x.js", importPath: "" })).toEqual({ allow: true, reason: "no import to judge" });
    expect(decide({ ...base, filePath: "src/x.js", importPath: 7 }).reason).toMatch(/^blocked: importPath must be a string\./);
  });
});
