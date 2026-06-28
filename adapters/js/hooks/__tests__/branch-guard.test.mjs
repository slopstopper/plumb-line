import { describe, it, expect } from "vitest";
import { decide } from "../branch-guard.mjs";

const cfg = {
  protectedBranches: ["main"],
  docsAllowlist: ["docs/", "README.md"],
};

describe("branch-guard decide", () => {
  it("blocks a code edit on a protected branch", () => {
    const r = decide({ filePath: "src/app.js", branch: "main", ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/protected branch/i);
  });

  it("allows a docs edit on a protected branch", () => {
    const r = decide({ filePath: "docs/x.md", branch: "main", ...cfg });
    expect(r.allow).toBe(true);
  });

  it("allows any edit on a non-protected branch", () => {
    const r = decide({ filePath: "src/app.js", branch: "feature/x", ...cfg });
    expect(r.allow).toBe(true);
  });

  it("blocks path traversal through a docs directory entry", () => {
    const r = decide({
      filePath: "docs/../src/app.py",
      branch: "main",
      protectedBranches: ["main"],
      docsAllowlist: ["docs/", "README.md"],
    });
    expect(r.allow).toBe(false);
  });

  it("blocks a file that starts with a docs allowlist file entry but is a different file", () => {
    const r = decide({
      filePath: "README.md.bak",
      branch: "main",
      protectedBranches: ["main"],
      docsAllowlist: ["README.md"],
    });
    expect(r.allow).toBe(false);
  });

  it("throws when the docs allowlist contains an empty string entry", () => {
    expect(() =>
      decide({
        filePath: "src/app.js",
        branch: "main",
        protectedBranches: ["main"],
        docsAllowlist: [""],
      }),
    ).toThrow("docs allowlist entry must not be empty");
  });
});
