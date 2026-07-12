import { describe, it, expect } from "vitest";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { normalizeModuleName, matchesExtraModule } = require("../module-match.cjs");

describe("normalizeModuleName", () => {
  it("takes the basename after the last slash", () => {
    expect(normalizeModuleName("@myorg/myorg-data")).toBe("myorg-data");
    expect(normalizeModuleName("pkg/sub/myorg-data")).toBe("myorg-data");
  });
  it("strips a known extension", () => {
    expect(normalizeModuleName("./myorg-data.mjs")).toBe("myorg-data");
    expect(normalizeModuleName("myorg_data.py")).toBe("myorg-data");
  });
  it("treats - and _ as equivalent", () => {
    expect(normalizeModuleName("myorg_data")).toBe("myorg-data");
    expect(normalizeModuleName("myorg-data")).toBe("myorg-data");
  });
});

describe("matchesExtraModule", () => {
  const extras = new Set(["myorg-data"].map(normalizeModuleName));
  it("matches across scope, path, separator, extension", () => {
    for (const s of ["@myorg/myorg-data", "pkg/myorg-data", "./myorg_data.mjs", "myorg_data"]) {
      expect(matchesExtraModule(s, extras)).toBe(true);
    }
  });
  it("does not match a different basename", () => {
    expect(matchesExtraModule("pkg/other", extras)).toBe(false);
  });
});
