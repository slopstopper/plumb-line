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
});
