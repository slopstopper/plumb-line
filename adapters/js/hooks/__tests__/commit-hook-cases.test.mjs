// commit-hook-cases.test.mjs — runs adapters/commit-hook-cases.json against
// the JS branch guard's git commit hook (#464) and the pre-commit gate
// (#613), in a real temporary git repository per row. Twin: adapters/python/hooks/test_commit_hook_cases.py. As
// with hook-cases.json, the twins' parity is a data contract: a case lives in
// the table, so neither twin can quietly miss it.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, chmodSync, rmSync, copyFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tableProblems } from "../../../../primitives/conformance/table-guards.mjs";

const cases = JSON.parse(readFileSync(
  fileURLToPath(new URL("../../../commit-hook-cases.json", import.meta.url)), "utf8"));
// Each case kind and the hook its rows run. Python twin: _HOOKS.
const HOOKS = {
  commitHook: fileURLToPath(new URL("../branch-guard-commit.mjs", import.meta.url)),
  preCommitGate: fileURLToPath(new URL("../pre-commit-gate.mjs", import.meta.url)),
  // The PreToolUse guard itself, where a row needs a real repository (#615).
  branchGuard: fileURLToPath(new URL("../branch-guard.mjs", import.meta.url)),
};

// Every field, case kind and table version this runner interprets (#441).
// Python twin: _MODEL in adapters/python/hooks/test_commit_hook_cases.py.
const ROW = ["name", "repo", "committed", "committedText", "fakeGit", "side", "branch", "tags", "headRef", "config", "merge",
  "rebaseStop", "rebaseApply", "rebaseAlso", "rebaseHeadName", "rebaseHeadNameDir", "rebaseUpdateRefsDir", "remove", "move", "stage", "stageHex", "gitlink", "stageCount", "modify", "env", "commit",
  "expectExit", "expectStderr"];
const MODEL = {
  versions: [1],
  meta: ["_doc", "version"],
  fields: { commitHook: ROW, preCommitGate: [...ROW, "gateCopy"], branchGuard: [...ROW, "stdin"] },
};
// A copy of the gate run in place of the shipped one: alone, or beside a
// guard or commit hook with none of the exports it reads (#613 review).
const GATE_COPIES = ["alone", "emptyWrapper", "emptyGuard"];

const isStrings = (v) => Array.isArray(v) && v.every((s) => typeof s === "string");
const isHex = (s) => typeof s === "string" && /^(?:[0-9a-fA-F]{2})+$/.test(s);

// The field types this runner reads, checked before a row runs, so both twins
// refuse the same rows. Python twin: _type_problems.
function typeProblems(c) {
  const problems = [];
  if (typeof c.name !== "string") problems.push("name must be a string");
  if ("repo" in c && c.repo !== false) problems.push("repo must be false when present");
  for (const f of ["committed", "side", "tags", "merge", "remove", "stage", "gitlink", "modify", "commit"]) {
    if (f in c && !isStrings(c[f])) problems.push(`${f} must be an array of strings`);
  }
  if ("branch" in c && c.branch !== null && typeof c.branch !== "string") problems.push("branch must be a string or null");
  if ("headRef" in c && typeof c.headRef !== "string") problems.push("headRef must be a string");
  if ("stageHex" in c && !(Array.isArray(c.stageHex) && c.stageHex.every(isHex))) {
    problems.push("stageHex must be an array of whole hex bytes");
  }
  for (const f of ["move", "config"]) {
    if (f in c && !(Array.isArray(c[f]) && c[f].every((m) => isStrings(m) && m.length === 2))) {
      problems.push(`${f} must be an array of pairs of strings`);
    }
  }
  if ("stageCount" in c && !(Array.isArray(c.stageCount) && c.stageCount.length === 2
      && typeof c.stageCount[0] === "string" && c.stageCount[0] !== ""
      && Number.isInteger(c.stageCount[1]) && c.stageCount[1] >= 1 && c.stageCount[1] <= 20000)) {
    problems.push("stageCount must be [a non-empty prefix, a count from 1 to 20000]");
  }
  if ("env" in c) {
    if (c.env === null || typeof c.env !== "object" || Array.isArray(c.env)) problems.push("env must be an object");
    else for (const [k, v] of Object.entries(c.env)) {
      if (v !== null && typeof v !== "string") problems.push(`env.${k} must be a string or null`);
    }
  }
  if ("committedText" in c && !(c.committedText !== null && typeof c.committedText === "object"
      && !Array.isArray(c.committedText) && Object.values(c.committedText).every((v) => typeof v === "string"))) {
    problems.push("committedText must be an object of strings");
  }
  if ("fakeGit" in c) {
    const f = c.fakeGit;
    if (f === null || typeof f !== "object" || Array.isArray(f) || typeof f.script !== "string"
        || typeof f.executable !== "boolean" || Object.keys(f).some((k) => k !== "script" && k !== "executable")) {
      problems.push("fakeGit must be {script: string, executable: boolean}");
    }
    if ("commit" in c) problems.push("fakeGit cannot be combined with commit");
  }
  if (!Number.isInteger(c.expectExit)) problems.push("expectExit must be an integer");
  if ("stdin" in c && typeof c.stdin !== "string") problems.push("stdin must be a string");
  if ("gateCopy" in c) {
    if (!GATE_COPIES.includes(c.gateCopy)) problems.push("gateCopy must be one of alone, emptyWrapper, emptyGuard");
    if ("commit" in c) problems.push("gateCopy cannot be combined with commit");
  }
  if (typeof c.expectStderr !== "string") problems.push("expectStderr must be a string");
  // A detached HEAD, a tag, a HEAD ref, a side branch or a gitlink needs a
  // commit to stand on, and a merge needs the side branch.
  if (!("committed" in c) && (c.branch === null || ["tags", "headRef", "side", "gitlink"].some((f) => f in c))) {
    problems.push("branch null, tags, headRef, side and gitlink need committed");
  }
  if ("merge" in c && !("side" in c)) problems.push("merge needs side");
  if ("rebaseStop" in c && typeof c.rebaseStop !== "string") problems.push("rebaseStop must be a string");
  if ("rebaseHeadName" in c && c.rebaseHeadName !== null && typeof c.rebaseHeadName !== "string") {
    problems.push("rebaseHeadName must be a string or null");
  }
  if ("rebaseHeadNameDir" in c && c.rebaseHeadNameDir !== true) problems.push("rebaseHeadNameDir must be true when present");
  if ("rebaseApply" in c && c.rebaseApply !== true) problems.push("rebaseApply must be true when present");
  if ("rebaseAlso" in c && typeof c.rebaseAlso !== "string") problems.push("rebaseAlso must be a string");
  if ("rebaseUpdateRefsDir" in c && c.rebaseUpdateRefsDir !== true) {
    problems.push("rebaseUpdateRefsDir must be true when present");
  }
  if (["rebaseApply", "rebaseAlso"].some((f) => f in c) && !("rebaseStop" in c)) {
    problems.push("rebaseApply and rebaseAlso need rebaseStop");
  }
  if ("rebaseApply" in c && "rebaseAlso" in c) problems.push("rebaseApply cannot be combined with rebaseAlso");
  if ("rebaseUpdateRefsDir" in c && !("rebaseAlso" in c)) problems.push("rebaseUpdateRefsDir needs rebaseAlso");
  if ("rebaseStop" in c && !("committed" in c)) problems.push("rebaseStop needs committed");
  if (("rebaseHeadName" in c || "rebaseHeadNameDir" in c) && !("rebaseStop" in c)) {
    problems.push("rebaseHeadName and rebaseHeadNameDir need rebaseStop");
  }
  return problems;
}

// The caller's git and plumb-line settings cannot leak in: every GIT_* and
// PLUMBLINE_* variable is removed (these tests may themselves run inside a
// git hook), and the global and system git config are not read, so a
// core.hooksPath or commit.gpgsign there changes nothing.
const BASE_ENV = {
  ...Object.fromEntries(Object.entries(process.env).filter(([k]) =>
    !k.startsWith("GIT_") && !k.startsWith("PLUMBLINE_") && k !== "PYTHONIOENCODING" && k !== "CLAUDE_PROJECT_DIR")),
  GIT_CONFIG_GLOBAL: os.devNull,
  GIT_CONFIG_NOSYSTEM: "1",
  GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.com",
  GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.com",
};

function git(cwd, args, input) {
  const r = spawnSync("git", args, { cwd, env: BASE_ENV, input });
  if (r.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${r.stderr}`);
  return r.stdout;
}

function write(repo, p, text) {
  mkdirSync(path.dirname(path.join(repo, p)), { recursive: true });
  writeFileSync(path.join(repo, p), text);
}

/** Build the row's repository, as the table's _doc orders it. Python twin: _build. */
function build(c) {
  const repo = mkdtempSync(path.join(os.tmpdir(), "plumb-line-commit-hook-"));
  git(repo, ["init", "-q"]);
  git(repo, ["symbolic-ref", "HEAD", "refs/heads/main"]);
  if (c.committed) {
    for (const p of c.committed) write(repo, p, "base\n");
    for (const [p, text] of Object.entries(c.committedText ?? {})) write(repo, p, text);
    git(repo, ["add", "--", ...c.committed, ...Object.keys(c.committedText ?? {})]);
    git(repo, ["commit", "-q", "--no-verify", "-m", "base"]);
  }
  if (c.side) {
    git(repo, ["checkout", "-q", "-b", "side"]);
    for (const p of c.side) write(repo, p, "side\n");
    git(repo, ["add", "--", ...c.side]);
    git(repo, ["commit", "-q", "--no-verify", "-m", "side"]);
    git(repo, ["checkout", "-q", "main"]);
  }
  if (c.branch === null) git(repo, ["checkout", "-q", "--detach"]);
  else if (c.branch !== undefined && c.branch !== "main") git(repo, ["checkout", "-q", "-b", c.branch]);
  for (const t of c.tags ?? []) git(repo, ["tag", t]);
  if (c.headRef !== undefined) git(repo, ["symbolic-ref", "HEAD", c.headRef]);
  for (const [k, v] of c.config ?? []) git(repo, ["config", k, v]);
  if (c.merge) git(repo, ["merge", "-q", ...c.merge]);
  if (c.rebaseStop !== undefined) {
    write(repo, c.rebaseStop, "rebased\n");
    if (c.rebaseApply) write(repo, "conflict.txt", "branch\n");
    git(repo, ["add", "--", c.rebaseStop, ...(c.rebaseApply ? ["conflict.txt"] : [])]);
    git(repo, ["commit", "-q", "--no-verify", "-m", "rebased"]);
    let args = ["rebase", "-q", "--exec", "false", "HEAD~1"];
    if (c.rebaseApply) {
      // The apply backend has no --exec: it stops on an add/add conflict,
      // with rebase-apply/head-name written.
      const name = git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]).toString().trim();
      git(repo, ["checkout", "-q", "-b", "apply-onto", "HEAD~1"]);
      write(repo, "conflict.txt", "onto\n");
      git(repo, ["add", "--", "conflict.txt"]);
      git(repo, ["commit", "-q", "--no-verify", "-m", "onto"]);
      git(repo, ["checkout", "-q", name]);
      args = ["rebase", "-q", "--apply", "apply-onto"];
    } else if (c.rebaseAlso !== undefined) {
      // --update-refs: rebaseAlso points at the commit the rebase stops on,
      // so the rebase will move it too.
      git(repo, ["branch", "-f", c.rebaseAlso, "HEAD"]);
      write(repo, "tip.md", "tip\n");
      git(repo, ["add", "--", "tip.md"]);
      git(repo, ["commit", "-q", "--no-verify", "-m", "tip"]);
      args = ["rebase", "-q", "--update-refs", "--exec", "false", "HEAD~2"];
    }
    // --exec false stops the rebase after the commit is replayed, with HEAD
    // detached and rebase-merge/head-name written, as an `edit` stop is.
    const r = spawnSync("git", args, { cwd: repo, env: BASE_ENV });
    if (r.status === 0) throw new Error(`git ${args.join(" ")} did not stop`);
    const dir = git(repo, ["rev-parse", "--git-path", c.rebaseApply ? "rebase-apply" : "rebase-merge"]).toString().trim();
    if (c.rebaseUpdateRefsDir) {
      rmSync(path.resolve(repo, dir, "update-refs"));
      mkdirSync(path.resolve(repo, dir, "update-refs"));
    }
    const headName = path.resolve(repo, dir, "head-name");
    if (c.rebaseHeadNameDir) {
      rmSync(headName);
      mkdirSync(headName);
    } else if (c.rebaseHeadName === null) rmSync(headName);
    else if (c.rebaseHeadName !== undefined) writeFileSync(headName, c.rebaseHeadName);
  }
  for (const p of c.remove ?? []) git(repo, ["rm", "-q", "--", p]);
  for (const [from, to] of c.move ?? []) {
    mkdirSync(path.dirname(path.join(repo, to)), { recursive: true });
    git(repo, ["mv", "--", from, to]);
  }
  for (const p of c.stage ?? []) write(repo, p, "staged\n");
  if (c.stage?.length) git(repo, ["add", "--", ...c.stage]);
  // Index only: a path that is not UTF-8 cannot be created on every
  // filesystem (APFS refuses it), but git's index takes any bytes, and
  // thousands of paths are staged without writing thousands of files.
  const indexOnly = [
    ...(c.stageHex ?? []).map((h) => ["100644", Buffer.from(h, "hex")]),
    ...(c.gitlink ?? []).map((p) => ["160000", Buffer.from(p)]),
  ];
  if (c.stageCount) {
    for (let i = 0; i < c.stageCount[1]; i++) indexOnly.push(["100644", Buffer.from(`${c.stageCount[0]}${i}`)]);
  }
  if (indexOnly.length) {
    const blob = git(repo, ["hash-object", "-w", "--stdin"], "staged\n").toString().trim();
    const head = c.gitlink ? git(repo, ["rev-parse", "HEAD"]).toString().trim() : "";
    const info = Buffer.concat(indexOnly.map(([mode, p]) =>
      Buffer.concat([Buffer.from(`${mode} ${mode === "160000" ? head : blob}\t`), p, Buffer.from([0])])));
    git(repo, ["update-index", "-z", "--add", "--index-info"], info);
  }
  for (const p of c.modify ?? []) write(repo, p, "modified\n");
  return repo;
}

function run(c, kind = "commitHook") {
  let HOOK = HOOKS[kind];
  const env = { ...BASE_ENV };
  for (const [k, v] of Object.entries(c.env ?? {})) {
    if (v === null) delete env[k];
    else env[k] = v;
  }
  const options = { env, encoding: "utf8", timeout: 30_000 }; // a hang fails its row
  if (kind === "branchGuard") options.input = c.stdin ?? "";
  if (c.gateCopy !== undefined) {
    // Python twin: the same three copies, with an empty module standing in
    // for an older guard or commit hook.
    const dir = mkdtempSync(path.join(os.tmpdir(), "plumb-line-gate-copy-"));
    const hooks = path.dirname(HOOK);
    copyFileSync(HOOK, path.join(dir, path.basename(HOOK)));
    if (c.gateCopy === "emptyWrapper") {
      copyFileSync(path.join(hooks, "branch-guard.mjs"), path.join(dir, "branch-guard.mjs"));
      writeFileSync(path.join(dir, "branch-guard-commit.mjs"), "");
    } else if (c.gateCopy === "emptyGuard") {
      copyFileSync(path.join(hooks, "branch-guard-commit.mjs"), path.join(dir, "branch-guard-commit.mjs"));
      writeFileSync(path.join(dir, "branch-guard.mjs"), "");
    }
    HOOK = path.join(dir, path.basename(HOOK));
  }
  if (c.repo === false) {
    const cwd = mkdtempSync(path.join(os.tmpdir(), "plumb-line-no-repo-"));
    env.GIT_CEILING_DIRECTORIES = path.dirname(cwd);
    return spawnSync(process.execPath, [HOOK], { ...options, cwd });
  }
  const repo = build(c);
  if (c.fakeGit) {
    const bin = mkdtempSync(path.join(os.tmpdir(), "plumb-line-fake-git-"));
    writeFileSync(path.join(bin, "git"), c.fakeGit.script);
    chmodSync(path.join(bin, "git"), c.fakeGit.executable ? 0o755 : 0o644);
    env.PATH = bin;
  }
  if (c.commit === undefined) return spawnSync(process.execPath, [HOOK], { ...options, cwd: repo });
  const hook = path.join(repo, ".git", "hooks", "pre-commit");
  writeFileSync(hook, `#!/bin/sh\nexec '${process.execPath}' '${HOOK}'\n`);
  chmodSync(hook, 0o755);
  const head = () => spawnSync("git", ["rev-parse", "-q", "--verify", "HEAD"], { cwd: repo, env: BASE_ENV, encoding: "utf8" }).stdout;
  const before = head();
  const r = spawnSync("git", ["commit", "-q", "-m", "case", ...c.commit], { ...options, cwd: repo });
  return { ...r, committed: head() !== before };
}

describe("commit-hook-cases.json — the runner interprets every field, kind and version", () => {
  it("the shipped table has nothing this runner ignores", () => {
    expect(tableProblems(cases, MODEL)).toEqual([]);
  });
  it("a planted unknown field fails", () => {
    const t = structuredClone(cases);
    t.commitHook[0].surprise = 1;
    expect(tableProblems(t, MODEL)).toEqual([expect.stringContaining("unknown field(s) surprise")]);
  });
  it("a planted unknown kind or version fails", () => {
    expect(tableProblems({ ...structuredClone(cases), pushHook: [] }, MODEL))
      .toEqual([expect.stringContaining("unknown case kind pushHook")]);
    expect(tableProblems({ ...structuredClone(cases), version: 2 }, MODEL))
      .toEqual([expect.stringContaining("unknown case-table version 2")]);
  });
  it("every row's fields have the types this runner reads", () => {
    const problems = Object.keys(HOOKS).flatMap((kind) => cases[kind].flatMap((c) =>
      typeProblems(c).map((p) => `${kind} ${JSON.stringify(c.name)}: ${p}`)));
    expect(problems).toEqual([]);
  });
  it("a planted wrong type fails", () => {
    const ok = { name: "x", expectExit: 0, expectStderr: "" };
    expect(typeProblems({ ...ok, stage: "src/a.js" })).toEqual(["stage must be an array of strings"]);
    expect(typeProblems({ ...ok, stageHex: ["ff0"] })).toEqual(["stageHex must be an array of whole hex bytes"]);
    expect(typeProblems({ ...ok, move: [["a"]] })).toEqual(["move must be an array of pairs of strings"]);
    expect(typeProblems({ ...ok, config: [["a", 1]] })).toEqual(["config must be an array of pairs of strings"]);
    expect(typeProblems({ ...ok, stageCount: ["p", 0] }))
      .toEqual(["stageCount must be [a non-empty prefix, a count from 1 to 20000]"]);
    expect(typeProblems({ ...ok, committed: [], merge: ["side"] })).toEqual(["merge needs side"]);
    expect(typeProblems({ ...ok, committedText: { a: 1 } })).toEqual(["committedText must be an object of strings"]);
    expect(typeProblems({ ...ok, fakeGit: { script: "x" } })).toEqual(["fakeGit must be {script: string, executable: boolean}"]);
    expect(typeProblems({ ...ok, fakeGit: { script: "x", executable: true }, commit: [] }))
      .toEqual(["fakeGit cannot be combined with commit"]);
    expect(typeProblems({ ...ok, branch: 1 })).toEqual(["branch must be a string or null"]);
    expect(typeProblems({ ...ok, repo: true })).toEqual(["repo must be false when present"]);
    expect(typeProblems({ ...ok, env: { A: 1 } })).toEqual(["env.A must be a string or null"]);
    expect(typeProblems({ ...ok, branch: null })).toEqual(["branch null, tags, headRef, side and gitlink need committed"]);
    expect(typeProblems({ name: "x", expectExit: 2.5 }))
      .toEqual(["expectExit must be an integer", "expectStderr must be a string"]);
  });
  // The acceptance of #464 names these four; a table edit cannot drop one.
  it("covers a protected branch, an unprotected branch, a detached HEAD and a docs-only commit", () => {
    const names = cases.commitHook.map((c) => c.name).join("\n");
    for (const kind of ["on a protected branch blocks", "on an unprotected branch passes",
      "detached HEAD blocks", "docs-only commit on a protected branch passes"]) {
      expect(names).toContain(kind);
    }
  });
  // The branch-aware gate's cases (#613); a table edit cannot drop one.
  it("covers the cases #613 names", () => {
    const names = cases.preCommitGate.map((c) => c.name).join("\n");
    for (const kind of ["with no PLUMBLINE_CFG the tests run on any branch and a failure blocks",
      "on a protected branch failing tests block", "testsOnOtherBranches absent the tests are not run",
      '"skip" the tests are not run', '"run" failing tests are allowed',
      '"run" passing tests are allowed, silently', 'other than "skip" or "run" blocks',
      "an unset PLUMBLINE_TEST_CMD blocks even where the tests would be skipped",
      "on a detached HEAD failing tests block", "--update-refs that will move main"]) {
      expect(names).toContain(kind);
    }
  });
});

for (const [kind, title] of [
  ["commitHook", "commit hook cases — JS wrapper in a real git repository"],
  ["preCommitGate", "pre-commit gate cases — JS gate in a real git repository"],
  ["branchGuard", "branch guard cases — JS PreToolUse guard in a real git repository"],
]) describe(title, () => {
  for (const c of cases[kind]) {
    it(c.name, () => {
      expect(typeProblems(c)).toEqual([]);
      const r = run(c, kind);
      expect(r.error, "the hook did not start, or timed out").toBeUndefined();
      expect(r.status, r.stderr).toBe(c.expectExit);
      expect(r.stderr).toBe(c.expectStderr);
      // A commit row that passes made a commit; one that blocks made none.
      if (c.commit !== undefined) expect(r.committed, "a commit was made").toBe(c.expectExit === 0);
    });
  }
});
