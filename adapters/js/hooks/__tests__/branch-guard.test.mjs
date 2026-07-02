import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
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
  function runCli(filePath) {
    return spawnSync("node", [guardPath], {
      input: JSON.stringify({ filePath }),
      encoding: "utf8",
      env: {
        ...process.env,
        PLUMBLINE_BRANCH: "main",
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
});
