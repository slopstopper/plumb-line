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
      importPath: "./b.js",
      ...cfg,
    });
    expect(r.allow).toBe(true);
  });
});
