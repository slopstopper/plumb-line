// branch-guard-commit.mjs — run the branch guard as a git pre-commit hook (#464).
//
// Git gives a commit hook neither the {filePath} stdin nor PLUMBLINE_BRANCH
// the branch guard reads, so wired in directly the guard blocks every commit.
// This wrapper works both out from git and judges each staged path with the
// guard's own decide() and PLUMBLINE_CFG checks, in-process: one Node start
// per commit, not one per file. Copy it next to branch-guard.mjs, which it
// imports. Python twin: branch_guard_commit.py. Cases:
// adapters/commit-hook-cases.json.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { configFromEnv, decide, isBranchName, isCaseAlias, readIgnoreCase } from "./branch-guard.mjs";

/**
 * The branch HEAD names, from `git symbolic-ref HEAD`'s full ref, or null when
 * HEAD is on no branch (detached, or pointing outside refs/heads/). The full
 * ref, never --short: git shortens refs/heads/main to "heads/main" when a tag
 * named main exists, and that string is not a protected branch.
 */
export function branchFromRef(ref) {
  return ref.startsWith("refs/heads/") ? ref.slice("refs/heads/".length) : null;
}

/**
 * The staged paths from `git diff --cached --name-only -z` output. Git paths
 * are bytes: each is decoded as UTF-8 with U+FFFD for a bad sequence, as the
 * Python twin's errors="replace" does (the two agree sequence for sequence),
 * so a path that is not UTF-8 is still judged, not refused.
 */
export function stagedPaths(output) {
  const decoder = new TextDecoder("utf-8", { ignoreBOM: true });
  const parts = [];
  let start = 0;
  for (let i = 0; i < output.length; i++) {
    if (output[i] === 0) {
      parts.push(decoder.decode(output.subarray(start, i)));
      start = i + 1;
    }
  }
  return parts;
}

// A file git records for a rebase, decoded as the staged paths are: UTF-8
// with U+FFFD for a bad sequence, and a leading BOM kept, as Python keeps it.
const decodeState = (bytes) => new TextDecoder("utf-8", { ignoreBOM: true }).decode(bytes);

// What a rebase-merge or rebase-apply directory is named for in a reason:
// `git am` also stops in rebase-apply, and writes no head-name.
const operation = (dir) => (dir === "rebase-apply" ? "a rebase or git am" : "a rebase");

/**
 * The branch a rebase in progress is rebasing (#547), from the head-name file
 * git records in its rebase-merge or rebase-apply directory, given the
 * file's bytes (null when it cannot be read) and the read error's code.
 * Returns { branch } for a branch; for anything else, the branch as far as it
 * is known and `why`, the reason it cannot be used. Python twin:
 * rebase_branch.
 */
export function rebaseBranch(dir, bytes, code) {
  if (bytes === null) {
    return { branch: null, why: `HEAD is detached by ${operation(dir)} whose ${dir}/head-name cannot be read: ${code}` };
  }
  const ref = decodeState(bytes).replace(/\n$/, "");
  const branch = branchFromRef(ref);
  if (branch === null) {
    return { branch: null, why: `HEAD is detached by ${operation(dir)} of ${JSON.stringify(ref)}, which is not a branch` };
  }
  if (!isBranchName(branch)) {
    return { branch, why: `HEAD is detached by ${operation(dir)} of ${JSON.stringify(branch)}, which is not a branch name` };
  }
  return { branch };
}

/**
 * The other branches a rebase with --update-refs will move (#547 review),
 * from its update-refs file: each ref takes three lines, the ref and two
 * object ids, and only refs/heads/ refs are branches. Python twin:
 * update_ref_branches.
 */
export function updateRefBranches(bytes) {
  const lines = decodeState(bytes).split("\n");
  const branches = [];
  for (let i = 0; i < lines.length; i += 3) {
    const branch = branchFromRef(lines[i]);
    if (branch !== null) branches.push(branch);
  }
  return branches;
}

/**
 * Judge a commit: every staged path through decide(), stopping at the first
 * block. The branch is unknown when HEAD is on no branch (`branch` null) or on
 * one git would not accept as a branch name, such as `-x`, which
 * `git symbolic-ref` can still point HEAD at: then only a path allowed on
 * every branch passes (#449). With the config already checked and a non-empty
 * path, decide()'s only block on an unknown branch is the code edit, so that
 * reason is replaced with one naming HEAD rather than PLUMBLINE_BRANCH, which
 * this hook never reads; `why`, when given, says why the branch is unknown
 * (a rebase in progress, #547). `ignoreCase`: git ignores case here, so a
 * case alias of a protected branch is protected (#615).
 */
export function judgeCommit({ branch, paths, config, why: given, ignoreCase = false }) {
  const known = branch !== null && isBranchName(branch);
  for (const filePath of paths) {
    const r = decide({
      filePath,
      branch: branch ?? "",
      protectedBranches: config.protectedBranches,
      docsAllowlist: config.docsAllowlist,
      ignoreCase,
    });
    if (r.allow) continue;
    if (known) return r;
    const why = given ?? (branch === null
      ? "HEAD is not on a branch"
      : `HEAD is on ${JSON.stringify(branch)}, which is not a branch name`);
    return {
      allow: false,
      reason: `blocked: code edit to ${filePath} with the branch unknown (${why}). Switch to a branch first.`,
    };
  }
  return { allow: true, reason: "no staged path is blocked" };
}

/* v8 ignore start -- the CLI is exercised by spawning it (commit-hook-cases.test.mjs) */
function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(fileURLToPath(import.meta.url)) === fs.realpathSync(process.argv[1]);
  } catch {
    return false;
  }
}

/**
 * A git step that failed: what could not be done, without a subject, such as
 * "could not read the branch (git symbolic-ref exited 128)", for the caller
 * to name itself in. Python twin: GitRefused.
 */
export class GitRefused extends Error {}

/**
 * Run git; the finished process, or throw GitRefused saying why not. No
 * output limit: Node's default of 1 MiB blocked a large commit (vendored
 * files) on any branch, where the Python twin read it all. Reasons match the
 * twin's: the errno name when git cannot start, the signal's name when it is
 * killed.
 */
function git(args, what, okStatuses = [0]) {
  const r = spawnSync("git", args, { stdio: ["ignore", "pipe", "pipe"], maxBuffer: Infinity });
  if (r.error) throw new GitRefused(`could not run git (${r.error.code ?? r.error.message})`);
  if (r.signal) throw new GitRefused(`could not ${what} (git ${args[0]} was killed by ${r.signal})`);
  if (!okStatuses.includes(r.status)) {
    throw new GitRefused(`could not ${what} (git ${args[0]} exited ${r.status})`);
  }
  return r;
}

/**
 * The branch a commit made now lands on, read from git as this hook reads it:
 * `{ branch, why, also, alsoWhy }`. `branch` is null on no branch; `why`,
 * when set, says why the branch is unknown; `also` lists the other branches a
 * rebase with --update-refs will move, and `alsoWhy` says why they cannot be
 * read. Throws GitRefused when a git step fails. Shared with the pre-commit
 * gate (#613), so the two read the same branch. Python twin: resolve_branch.
 */
export function resolveBranch() {
  // --quiet: exit 1, silently, when HEAD is detached.
  const head = git(["symbolic-ref", "--quiet", "HEAD"], "read the branch", [0, 1]);
  let branch = head.status === 0
    ? branchFromRef(new TextDecoder().decode(head.stdout).replace(/\n$/, ""))
    : null;
  let why;
  let also = [];
  let alsoWhy;
  // HEAD is detached during a rebase (#547). While git's rebase directory
  // exists, which git itself reads as a rebase in progress, the branch is the
  // one it records as being rebased, and with --update-refs every other
  // branch it will move is judged too. With no rebase directory a detached
  // HEAD stays unknown (#449).
  if (head.status !== 0) {
    for (const dir of ["rebase-merge", "rebase-apply"]) {
      const where = new TextDecoder().decode(git(["rev-parse", "--git-path", dir], "find the rebase state").stdout)
        .replace(/\n$/, "");
      if (!fs.existsSync(where)) continue;
      let bytes = null;
      let code;
      try {
        bytes = fs.readFileSync(path.join(where, "head-name"));
      } catch (e) {
        code = e.code ?? e.message;
      }
      ({ branch = null, why } = rebaseBranch(dir, bytes, code));
      const updateRefs = path.join(where, "update-refs");
      if (fs.existsSync(updateRefs)) {
        try {
          also = updateRefBranches(fs.readFileSync(updateRefs));
        } catch (e) {
          alsoWhy = `HEAD is detached by a rebase whose ${dir}/update-refs cannot be read: ${e.code ?? e.message}`;
        }
      }
      break;
    }
  }
  return { branch, why, also, alsoWhy };
}

function main() {
  // The config first: a bad PLUMBLINE_CFG blocks whatever is staged.
  const { config, reason } = configFromEnv();
  if (reason) return { allow: false, reason };
  const { branch, why, also, alsoWhy } = resolveBranch();
  // --cached against HEAD (or the empty tree on an unborn branch), in the
  // index git is committing: during `git commit -a` or `git commit <path>`
  // that is the temporary index GIT_INDEX_FILE names. --no-renames: a rename
  // is listed as the path it leaves and the path it makes, so moving a code
  // file into docs/ is judged by the code path it deletes.
  // --ignore-submodules=none: diff.ignoreSubmodules or a submodule's
  // `ignore` setting would otherwise hide a staged submodule bump.
  const diff = git(["diff", "--cached", "--name-only", "-z", "--no-renames", "--ignore-submodules=none"],
    "list the staged files");
  const paths = stagedPaths(diff.stdout);
  // core.ignorecase is read only when it decides (#615); unreadable fails closed.
  const protectedBranches = config.protectedBranches ?? ["main"];
  const ignoreCase = [branch, ...also].some((b) => b !== null && isCaseAlias(b, protectedBranches))
    && readIgnoreCase();
  const r = judgeCommit({ branch, paths, config, why, ignoreCase });
  if (!r.allow) return r;
  // Every branch the rebase will move must allow the commit (#547 review).
  if (alsoWhy !== undefined) return judgeCommit({ branch: null, paths, config, why: alsoWhy });
  for (const other of also) {
    const r2 = judgeCommit({ branch: other, paths, config, ignoreCase,
      why: `the rebase also moves ${JSON.stringify(other)}, which is not a branch name` });
    if (!r2.allow) return r2;
  }
  return r;
}

if (isMainModule()) {
  // Exit 2 on every block and failure, as the guards do; git refuses the
  // commit on any non-zero exit.
  let r;
  try {
    r = main();
  } catch (e) {
    r = {
      allow: false,
      reason: e instanceof GitRefused ? `blocked: the branch guard's commit hook ${e.message}.` : `blocked: ${e.message}`,
    };
  }
  if (!r.allow) {
    process.stderr.write(r.reason + "\n");
    process.exitCode = 2;
  }
}
/* v8 ignore stop */
