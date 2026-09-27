import { describe, it, expect } from "vitest";
import { decide } from "../branch-guard.mjs";

const cfg = {
  protectedBranches: ["main"],
  docsAllowlist: ["docs/", "README.md"],
};

describe("branch-guard decide", () => {
  // #449: "branch unknown" is an inconclusive result, never a pass. A code
  // edit's answer depends on the branch, so it blocks; a docs-allowlisted edit
  // is allowed on every branch, so it stays allowed.
  for (const branch of [undefined, null, "", "  "]) {
    it(`blocks a code edit when the branch is unknown (${JSON.stringify(branch)})`, () => {
      const r = decide({ filePath: "src/app.js", branch, ...cfg });
      expect(r.allow).toBe(false);
      expect(r.reason).toMatch(/branch unknown/i);
    });
  }

  // #449 review: a missing or non-string filePath (an unmapped host payload)
  // crashed the JS twin (exit 1, which Claude Code does not treat as a block).
  for (const filePath of [undefined, null, 5, ""]) {
    it(`blocks when there is no file path to judge (${JSON.stringify(filePath)}) on a protected branch`, () => {
      const r = decide({ filePath, branch: "main", ...cfg });
      expect(r.allow).toBe(false);
      expect(r.reason).toMatch(/no file path/i);
    });
  }

  it("blocks when there is no file path and the branch is unknown", () => {
    const r = decide({ filePath: undefined, branch: undefined, ...cfg });
    expect(r.allow).toBe(false);
  });

  it("allows an edit with no file path on an unprotected branch, as it allows any edit there", () => {
    expect(decide({ filePath: undefined, branch: "feature/x", ...cfg }).allow).toBe(true);
  });

  // Blank means ASCII whitespace in both twins (JS trim() and Python strip()
  // disagree on a few Unicode characters).
  for (const branch of ["\ufeff", "\x85"]) {
    it(`reads ${JSON.stringify(branch)} as a named, unprotected branch, as the Python twin does`, () => {
      expect(decide({ filePath: "src/app.js", branch, ...cfg }).allow).toBe(true);
    });
  }

  it("allows a docs edit when the branch is unknown", () => {
    const r = decide({ filePath: "docs/x.md", branch: undefined, ...cfg });
    expect(r.allow).toBe(true);
  });

  it("blocks an upward-escaping path when the branch is unknown", () => {
    const r = decide({ filePath: "../docs/x.md", branch: "", ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/branch unknown/i);
  });

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

  it("blocks a path that escapes upward on a protected branch", () => {
    const r = decide({ filePath: "../secret.js", branch: "main", ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/protected branch/i);
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

  it("allows files matching a '*.ext' extension glob at any depth", () => {
    const glob = {
      protectedBranches: ["main"],
      docsAllowlist: ["*.md"],
    };
    expect(
      decide({ filePath: "README.md", branch: "main", ...glob }).allow,
    ).toBe(true);
    expect(
      decide({ filePath: "docs/guide/intro.md", branch: "main", ...glob })
        .allow,
    ).toBe(true);
  });

  it("blocks files that do not match the '*.ext' extension glob", () => {
    const glob = {
      protectedBranches: ["main"],
      docsAllowlist: ["*.md"],
    };
    expect(
      decide({ filePath: "src/app.js", branch: "main", ...glob }).allow,
    ).toBe(false);
    // A name merely containing the extension chars but not ending in ".md".
    expect(
      decide({ filePath: "src/amd.js", branch: "main", ...glob }).allow,
    ).toBe(false);
  });
});

// CLI behaviour is in adapters/hook-cases.json, run against both twins by
// hook-cases.test.mjs (#475).
