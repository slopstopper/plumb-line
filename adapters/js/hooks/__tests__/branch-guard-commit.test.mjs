// branch-guard-commit.test.mjs — the git commit hook's pure parts, and the
// hook as bootstrap Step 4 wires it (#464). Behaviour against a real
// repository is the shared table's (commit-hook-cases.test.mjs). Python twin:
// adapters/python/hooks/test_branch_guard_commit.py.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { branchFromRef, judgeCommit, stagedPaths } from "../branch-guard-commit.mjs";

describe("branchFromRef", () => {
  it("strips refs/heads/ from a branch ref, slashes kept", () => {
    expect(branchFromRef("refs/heads/main")).toBe("main");
    expect(branchFromRef("refs/heads/release/1.x")).toBe("release/1.x");
  });
  it("is null for a ref outside refs/heads/, or git's short form", () => {
    expect(branchFromRef("refs/tags/v1")).toBeNull();
    expect(branchFromRef("heads/main")).toBeNull();
    expect(branchFromRef("main")).toBeNull();
  });
});

describe("stagedPaths", () => {
  it("splits NUL-terminated paths, spaces and newlines kept", () => {
    expect(stagedPaths(Buffer.from("a b.md\0src/x\ny.js\0"))).toEqual(["a b.md", "src/x\ny.js"]);
  });
  it("is empty for nothing staged", () => {
    expect(stagedPaths(Buffer.alloc(0))).toEqual([]);
  });
  it("decodes bytes that are not UTF-8 as U+FFFD, and keeps a byte-order mark", () => {
    expect(stagedPaths(Buffer.from("7372632fff2e6a7300efbbbf612e6d6400", "hex")))
      .toEqual(["src/�.js", "﻿a.md"]);
  });
});

describe("judgeCommit", () => {
  const docs = { docsAllowlist: ["docs/"] };
  it("allows every path on an unprotected branch", () => {
    expect(judgeCommit({ branch: "feat", paths: ["src/a.js"], config: {} }).allow).toBe(true);
  });
  it("uses the guard's defaults with an empty config: main is protected", () => {
    expect(judgeCommit({ branch: "main", paths: ["src/a.js"], config: {} })).toEqual({
      allow: false,
      reason: "blocked: code edit to src/a.js on protected branch main. Branch first.",
    });
  });
  it("stops at the first blocked path", () => {
    const r = judgeCommit({ branch: "main", paths: ["docs/a.md", "src/b.js", "src/c.js"], config: docs });
    expect(r.reason).toContain("src/b.js");
  });
  it("names HEAD, not PLUMBLINE_BRANCH, when HEAD is on no branch", () => {
    const r = judgeCommit({ branch: null, paths: ["src/a.js"], config: {} });
    expect(r.reason).toBe(
      "blocked: code edit to src/a.js with the branch unknown (HEAD is not on a branch). Switch to a branch first.");
    expect(r.reason).not.toContain("PLUMBLINE_BRANCH");
  });
  it("allows docs with HEAD on no branch, and nothing staged anywhere", () => {
    expect(judgeCommit({ branch: null, paths: ["docs/a.md"], config: docs }).allow).toBe(true);
    expect(judgeCommit({ branch: "main", paths: [], config: {} }).allow).toBe(true);
  });
});

// The wiring bootstrap Step 4 writes: the wrapper copied next to the guard in
// .claude/guards/, and a pre-commit hook that runs it, then the test gate.
// Run through a real `git commit`, so the verification is of the wiring, not
// of the wrapper alone. Python twin: test_the_bootstrap_wiring_*.
describe("the hook as bootstrap Step 4 wires it", () => {
  const HOOKS = path.dirname(fileURLToPath(new URL("../branch-guard-commit.mjs", import.meta.url)));
  const env = {
    ...Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("GIT_") && !k.startsWith("PLUMBLINE_"))),
    GIT_CONFIG_GLOBAL: os.devNull, GIT_CONFIG_NOSYSTEM: "1",
    GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.com", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.com",
  };
  const git = (cwd, ...args) => spawnSync("git", args, { cwd, env, encoding: "utf8" });

  function wiredRepo() {
    const repo = mkdtempSync(path.join(os.tmpdir(), "plumb-line-wiring-"));
    git(repo, "init", "-q");
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main");
    mkdirSync(path.join(repo, ".claude", "guards"), { recursive: true });
    for (const f of ["branch-guard.mjs", "branch-guard-commit.mjs", "pre-commit-gate.mjs"]) {
      copyFileSync(path.join(HOOKS, f), path.join(repo, ".claude", "guards", f));
    }
    const hooksDir = path.resolve(repo, git(repo, "rev-parse", "--git-path", "hooks").stdout.trim());
    mkdirSync(hooksDir, { recursive: true });
    const hook = path.join(hooksDir, "pre-commit");
    writeFileSync(hook, [
      "#!/bin/sh",
      "# plumb-line (bootstrap Step 4): the branch guard, then the test gate.",
      `PLUMBLINE_CFG='{"protectedBranches": ["main"], "docsAllowlist": ["docs/", "*.md"]}'`,
      "export PLUMBLINE_CFG",
      `'${process.execPath}' .claude/guards/branch-guard-commit.mjs || exit 1`,
      `PLUMBLINE_TEST_CMD="'${process.execPath}' -e ''" exec '${process.execPath}' .claude/guards/pre-commit-gate.mjs`,
      "",
    ].join("\n"));
    chmodSync(hook, 0o755);
    writeFileSync(path.join(repo, "README.md"), "base\n");
    git(repo, "add", "README.md");
    expect(git(repo, "commit", "-q", "-m", "base").status).toBe(0); // docs on main: allowed
    return repo;
  }

  const stage = (repo, p) => {
    mkdirSync(path.dirname(path.join(repo, p)), { recursive: true });
    writeFileSync(path.join(repo, p), "x\n");
    git(repo, "add", p);
  };
  const head = (repo) => git(repo, "rev-parse", "HEAD").stdout;

  it("refuses a code commit on main with the guard's reason, and makes no commit", () => {
    const repo = wiredRepo();
    const before = head(repo);
    stage(repo, "src/a.js");
    const r = git(repo, "commit", "-q", "-m", "code");
    expect(r.status).toBe(1);
    expect(r.stderr).toBe("blocked: code edit to src/a.js on protected branch main. Branch first.\n");
    expect(head(repo)).toBe(before);
  });
  it("commits docs on main, and code once the change is on a branch", () => {
    const repo = wiredRepo();
    stage(repo, "docs/guide.md");
    expect(git(repo, "commit", "-q", "-m", "docs").status).toBe(0);
    stage(repo, "src/a.js");
    git(repo, "switch", "-q", "-c", "feat"); // the staged change comes along
    const r = git(repo, "commit", "-q", "-m", "code");
    expect(r.stderr).toBe("");
    expect(r.status).toBe(0);
  });
  it("still runs the test gate after the branch guard passes", () => {
    const repo = wiredRepo();
    const hook = path.resolve(repo, git(repo, "rev-parse", "--git-path", "hooks").stdout.trim(), "pre-commit");
    // A failing test command: the gate, not the branch guard, refuses.
    writeFileSync(hook, `#!/bin/sh\n'${process.execPath}' .claude/guards/branch-guard-commit.mjs || exit 1\n`
      + `PLUMBLINE_TEST_CMD="'${process.execPath}' -e 'process.exit(1)'" exec '${process.execPath}' .claude/guards/pre-commit-gate.mjs\n`);
    git(repo, "switch", "-q", "-c", "feat");
    stage(repo, "src/a.js");
    const r = git(repo, "commit", "-q", "-m", "code");
    expect(r.status).toBe(1);
    expect(r.stderr).toContain("pre-commit blocked:");
  });
});
