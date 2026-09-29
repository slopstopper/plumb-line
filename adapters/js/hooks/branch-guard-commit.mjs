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
import { fileURLToPath } from "node:url";
import { configFromEnv, decide, isBranchName } from "./branch-guard.mjs";

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

/**
 * Judge a commit: every staged path through decide(), stopping at the first
 * block. The branch is unknown when HEAD is on no branch (`branch` null) or on
 * one git would not accept as a branch name, such as `-x`, which
 * `git symbolic-ref` can still point HEAD at: then only a path allowed on
 * every branch passes (#449). With the config already checked and a non-empty
 * path, decide()'s only block on an unknown branch is the code edit, so that
 * reason is replaced with one naming HEAD rather than PLUMBLINE_BRANCH, which
 * this hook never reads.
 */
export function judgeCommit({ branch, paths, config }) {
  const known = branch !== null && isBranchName(branch);
  for (const filePath of paths) {
    const r = decide({
      filePath,
      branch: branch ?? "",
      protectedBranches: config.protectedBranches,
      docsAllowlist: config.docsAllowlist,
    });
    if (r.allow) continue;
    if (known) return r;
    const why = branch === null
      ? "HEAD is not on a branch"
      : `HEAD is on ${JSON.stringify(branch)}, which is not a branch name`;
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
 * Run git; the finished process, or throw with the reason to block. No output
 * limit: Node's default of 1 MiB blocked a large commit (vendored files) on
 * any branch, where the Python twin read it all. Reasons match the twin's:
 * the errno name when git cannot start, the signal's name when it is killed.
 */
function git(args, what, okStatuses = [0]) {
  const r = spawnSync("git", args, { stdio: ["ignore", "pipe", "pipe"], maxBuffer: Infinity });
  if (r.error) throw new Error(`the branch guard's commit hook could not run git (${r.error.code ?? r.error.message}).`);
  if (r.signal) throw new Error(`the branch guard's commit hook could not ${what} (git ${args[0]} was killed by ${r.signal}).`);
  if (!okStatuses.includes(r.status)) {
    throw new Error(`the branch guard's commit hook could not ${what} (git ${args[0]} exited ${r.status}).`);
  }
  return r;
}

function main() {
  // The config first: a bad PLUMBLINE_CFG blocks whatever is staged.
  const { config, reason } = configFromEnv();
  if (reason) return { allow: false, reason };
  // --quiet: exit 1, silently, when HEAD is detached.
  const head = git(["symbolic-ref", "--quiet", "HEAD"], "read the branch", [0, 1]);
  const branch = head.status === 0
    ? branchFromRef(new TextDecoder().decode(head.stdout).replace(/\n$/, ""))
    : null;
  // --cached against HEAD (or the empty tree on an unborn branch), in the
  // index git is committing: during `git commit -a` or `git commit <path>`
  // that is the temporary index GIT_INDEX_FILE names. --no-renames: a rename
  // is listed as the path it leaves and the path it makes, so moving a code
  // file into docs/ is judged by the code path it deletes.
  // --ignore-submodules=none: diff.ignoreSubmodules or a submodule's
  // `ignore` setting would otherwise hide a staged submodule bump.
  const diff = git(["diff", "--cached", "--name-only", "-z", "--no-renames", "--ignore-submodules=none"],
    "list the staged files");
  return judgeCommit({ branch, paths: stagedPaths(diff.stdout), config });
}

if (isMainModule()) {
  // Exit 2 on every block and failure, as the guards do; git refuses the
  // commit on any non-zero exit.
  let r;
  try {
    r = main();
  } catch (e) {
    r = { allow: false, reason: `blocked: ${e.message}` };
  }
  if (!r.allow) {
    process.stderr.write(r.reason + "\n");
    process.exitCode = 2;
  }
}
/* v8 ignore stop */
