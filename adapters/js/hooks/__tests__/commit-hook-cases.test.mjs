// commit-hook-cases.test.mjs — runs adapters/commit-hook-cases.json against
// the JS branch guard's git commit hook, in a real temporary git repository
// per row (#464). Twin: adapters/python/hooks/test_commit_hook_cases.py. As
// with hook-cases.json, the twins' parity is a data contract: a case lives in
// the table, so neither twin can quietly miss it.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tableProblems } from "../../../../primitives/conformance/table-guards.mjs";

const cases = JSON.parse(readFileSync(
  fileURLToPath(new URL("../../../commit-hook-cases.json", import.meta.url)), "utf8"));
const HOOK = fileURLToPath(new URL("../branch-guard-commit.mjs", import.meta.url));

// Every field, case kind and table version this runner interprets (#441).
// Python twin: _MODEL in adapters/python/hooks/test_commit_hook_cases.py.
const ROW = ["name", "repo", "committed", "committedText", "fakeGit", "side", "branch", "tags", "headRef", "config", "merge",
  "remove", "move", "stage", "stageHex", "gitlink", "stageCount", "modify", "env", "commit",
  "expectExit", "expectStderr"];
const MODEL = { versions: [1], meta: ["_doc", "version"], fields: { commitHook: ROW } };

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
  if (typeof c.expectStderr !== "string") problems.push("expectStderr must be a string");
  // A detached HEAD, a tag, a HEAD ref, a side branch or a gitlink needs a
  // commit to stand on, and a merge needs the side branch.
  if (!("committed" in c) && (c.branch === null || ["tags", "headRef", "side", "gitlink"].some((f) => f in c))) {
    problems.push("branch null, tags, headRef, side and gitlink need committed");
  }
  if ("merge" in c && !("side" in c)) problems.push("merge needs side");
  return problems;
}

// The caller's git and plumb-line settings cannot leak in: every GIT_* and
// PLUMBLINE_* variable is removed (these tests may themselves run inside a
// git hook), and the global and system git config are not read, so a
// core.hooksPath or commit.gpgsign there changes nothing.
const BASE_ENV = {
  ...Object.fromEntries(Object.entries(process.env).filter(([k]) =>
    !k.startsWith("GIT_") && !k.startsWith("PLUMBLINE_") && k !== "PYTHONIOENCODING")),
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

function run(c) {
  const env = { ...BASE_ENV };
  for (const [k, v] of Object.entries(c.env ?? {})) {
    if (v === null) delete env[k];
    else env[k] = v;
  }
  const options = { env, encoding: "utf8", timeout: 30_000 }; // a hang fails its row
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
    const problems = cases.commitHook.flatMap((c) => typeProblems(c).map((p) => `${JSON.stringify(c.name)}: ${p}`));
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
});

describe("commit hook cases — JS wrapper in a real git repository", () => {
  for (const c of cases.commitHook) {
    it(c.name, () => {
      expect(typeProblems(c)).toEqual([]);
      const r = run(c);
      expect(r.error, "the hook did not start, or timed out").toBeUndefined();
      expect(r.status, r.stderr).toBe(c.expectExit);
      expect(r.stderr).toBe(c.expectStderr);
      // A commit row that passes made a commit; one that blocks made none.
      if (c.commit !== undefined) expect(r.committed, "a commit was made").toBe(c.expectExit === 0);
    });
  }
});
