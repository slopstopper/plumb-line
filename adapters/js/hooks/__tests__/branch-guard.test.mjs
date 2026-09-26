import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
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

// Bug C regression: the guard must run as a CLI hook. A naive
// `import.meta.url === file://${argv[1]}` entry check fails on symlinked paths
// (macOS /tmp, /var) and the guard would silently exit 0 (fail-open). These
// tests exercise the real CLI path so a broken entry check is caught.
describe("branch-guard CLI", () => {
  const guardPath = fileURLToPath(
    new URL("../branch-guard.mjs", import.meta.url),
  );
  function runCli(filePath, branch = "main") {
    const env = { ...process.env };
    delete env.PLUMBLINE_BRANCH;
    if (branch !== null) env.PLUMBLINE_BRANCH = branch; // null = unset
    return spawnSync("node", [guardPath], {
      input: JSON.stringify({ filePath }),
      encoding: "utf8",
      env: {
        ...env,
        PLUMBLINE_CFG: JSON.stringify({
          protectedBranches: ["main"],
          docsAllowlist: ["docs/", "README.md"],
        }),
      },
    });
  }

  it("blocks a code edit with exit code 2 when invoked as a CLI hook", () => {
    const r = runCli("src/app.js");
    expect(r.status).toBe(2);
    expect(r.stderr).toMatch(/protected branch/i);
  });

  it("allows a docs edit with exit code 0 when invoked as a CLI hook", () => {
    const r = runCli("docs/x.md");
    expect(r.status).toBe(0);
  });

  // #449: until 0.11.4 an unset PLUMBLINE_BRANCH exited 0 on every edit.
  it("blocks a code edit with exit code 2 when PLUMBLINE_BRANCH is unset", () => {
    const r = runCli("src/app.js", null);
    expect(r.status).toBe(2);
    expect(r.stderr).toMatch(/branch unknown/i);
  });

  it("blocks a code edit when PLUMBLINE_BRANCH is empty (a detached HEAD)", () => {
    expect(runCli("src/app.js", "").status).toBe(2);
  });

  it("allows a docs edit when PLUMBLINE_BRANCH is unset", () => {
    expect(runCli("docs/x.md", null).status).toBe(0);
  });

  // In a Claude Code hook only exit 2 blocks; a crash (exit 1) lets the edit
  // through. Every CLI failure must exit 2 (#449 review).
  function runRaw(stdin) {
    return spawnSync("node", [guardPath], {
      input: stdin,
      encoding: "utf8",
      env: { ...process.env, PLUMBLINE_BRANCH: "main", PLUMBLINE_CFG: JSON.stringify(cfg) },
    });
  }

  it("exits 2 when stdin carries no filePath (an unmapped host payload)", () => {
    const r = runRaw(JSON.stringify({ tool_input: { file_path: "src/app.js" } }));
    expect(r.status).toBe(2);
    expect(r.stderr).toMatch(/no file path/i);
  });

  it("exits 2 on empty stdin", () => {
    expect(runRaw("").status).toBe(2);
  });

  it("exits 2 on stdin that is not JSON", () => {
    const r = runRaw("not json");
    expect(r.status).toBe(2);
    expect(r.stderr).toMatch(/branch guard/i);
  });
});
