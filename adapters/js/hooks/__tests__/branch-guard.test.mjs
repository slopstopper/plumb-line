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
});
