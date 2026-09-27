// branch-guard.mjs — block the first code edit on a protected branch.
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

/** A bare "*.ext" extension glob (no path separators). */
const EXTENSION_GLOB = /^\*\.[A-Za-z0-9.]+$/;

/** Collapse `.` and `..` segments using posix rules, without touching the filesystem. */
function normalizePath(p) {
  return path.posix.normalize(p);
}

/** Return true if the normalized candidate path matches a single allowlist entry. */
function matchesAllowlistEntry(normalizedCandidate, entry) {
  if (entry === "") {
    throw new Error("docs allowlist entry must not be empty");
  }
  if (EXTENSION_GLOB.test(entry)) {
    // Extension glob: "*.md" matches any file ending in ".md", at any depth.
    // The candidate is already guaranteed not to escape upward (see decide).
    const ext = entry.slice(1); // ".md"
    return normalizedCandidate.endsWith(ext);
  }
  const normalizedEntry = normalizePath(entry);
  if (entry.endsWith("/")) {
    // Directory entry: candidate must equal the dir or be inside it at a segment boundary.
    const dir = normalizedEntry.endsWith("/")
      ? normalizedEntry
      : normalizedEntry + "/";
    return (
      normalizedCandidate === normalizedEntry ||
      normalizedCandidate.startsWith(dir)
    );
  }
  // File entry: exact match only.
  return normalizedCandidate === normalizedEntry;
}

/** Characters git never allows in a ref name: ASCII controls, space, ~ ^ : ? * [ \ */
// eslint-disable-next-line no-control-regex -- matching control characters is the point
const BAD_REF_CHARS = /[\x00-\x20\x7f~^:?*[\\]/;

/**
 * True when git would accept `name` as a branch name, by git's own rule: `git
 * branch` refuses `HEAD` and a leading `-`, then applies check-ref-format to
 * `refs/heads/<name>` (#474). The table's rows are cross-checked against
 * `git check-ref-format --branch`. Python twin: _is_branch_name.
 */
function isBranchName(name) {
  if (name === "HEAD" || name.startsWith("-")) return false;
  if (BAD_REF_CHARS.test(name) || name.includes("..") || name.includes("@{") || name.endsWith(".")) {
    return false;
  }
  return name.split("/").every((c) => c !== "" && !c.startsWith(".") && !c.endsWith(".lock"));
}

function blocked(filePath, branch, unknown) {
  if (!unknown) {
    return {
      allow: false,
      reason: `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.`,
    };
  }
  const why = isBlank(branch)
    ? "PLUMBLINE_BRANCH is unset or empty"
    : `PLUMBLINE_BRANCH ${JSON.stringify(String(branch))} is not a branch name`;
  return {
    allow: false,
    reason: `blocked: code edit to ${filePath} with the branch unknown (${why}). Set it to the current branch.`,
  };
}

/** Unset, or ASCII whitespace only, as in the Python twin. */
function isBlank(branch) {
  return branch == null || !/[^ \t\n\r\f\v]/.test(String(branch));
}

export function decide({
  filePath,
  branch,
  protectedBranches = ["main"],
  docsAllowlist = [],
}) {
  // An unknown branch (unset, or empty as on a detached HEAD) is an
  // inconclusive result, never a pass (#449): judge the edit as if the branch
  // were protected, so only an edit allowed on every branch passes. A value
  // git would not accept as a branch name, such as `HEAD` or `main ` (#474),
  // is unknown too: it names no branch the edit could be on.
  const unknown = isBlank(branch) || !isBranchName(String(branch));
  if (!unknown && !protectedBranches.includes(branch)) {
    return { allow: true, reason: "not a protected branch" };
  }
  // No path to judge (an unmapped host payload) cannot be a docs edit.
  if (typeof filePath !== "string" || filePath === "") {
    return {
      allow: false,
      reason:
        "blocked: no file path to judge. Map the host payload's file path into the {filePath} stdin the branch guard reads.",
    };
  }
  // Normalize candidate first; an upward-escaping path is never a docs match.
  const normalizedCandidate = normalizePath(filePath);
  if (normalizedCandidate.startsWith("..")) {
    return blocked(filePath, branch, unknown);
  }
  const isDocs = docsAllowlist.some((entry) =>
    matchesAllowlistEntry(normalizedCandidate, entry),
  );
  if (isDocs)
    return {
      allow: true,
      reason: unknown
        ? "docs edit allowed on any branch"
        : "docs edit allowed on protected branch",
    };
  return blocked(filePath, branch, unknown);
}

/**
 * True when this module is the process entry point. Compares real (symlink-
 * resolved) paths: on macOS `/tmp` and `/var` are symlinks to `/private/...`,
 * so `import.meta.url` and `process.argv[1]` can name the same file by
 * different paths. A naive string compare misses that and the guard silently
 * never runs as a CLI hook (fail-open).
 */
function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    return (
      fs.realpathSync(fileURLToPath(import.meta.url)) ===
      fs.realpathSync(process.argv[1])
    );
    /* v8 ignore next 3 -- defensive fail-closed on realpath error; not reachable in-process */
  } catch {
    return false;
  }
}

// CLI wrapper: read {filePath} on stdin, branch from env, config from env JSON.
// Exercised end-to-end by the rows of adapters/hook-cases.json, which
// __tests__/hook-cases.test.mjs runs by spawning this file; v8's
// in-process instrumentation cannot see across the child process, so this glue
// is excluded from coverage rather than left falsely "uncovered".
/* v8 ignore start */
if (isMainModule()) {
  const chunks = [];
  process.stdin.on("data", (d) => chunks.push(d));
  process.stdin.on("end", () => {
    // Every failure exits 2 (#449 review): a Claude Code hook treats only
    // exit 2 as a block, so a crash's exit 1 would let the edit through.
    let r;
    try {
      // Stdin is strict UTF-8, as in the Python twin (#475): a lossy decode
      // judged a mangled path. A byte-order mark is kept, as Python keeps it.
      let raw;
      try {
        raw = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(Buffer.concat(chunks));
      } catch {
        throw new Error("stdin is not valid UTF-8");
      }
      // Empty means JSON whitespace only, as in the Python twin: trim() also
      // strips a byte-order mark, and Python's strip() also strips \x1c-\x1f.
      const input = /^[ \t\n\r]*$/.test(raw) ? {} : JSON.parse(raw);
      const cfg = process.env.PLUMBLINE_CFG
        ? JSON.parse(process.env.PLUMBLINE_CFG)
        : {};
      // Only the two documented config keys (the Python twin also accepts
      // snake_case spellings; #469 settles one set for both): a
      // spread let a config `branch` or `filePath` override the real ones.
      r = decide({
        filePath: input?.filePath,
        branch: process.env.PLUMBLINE_BRANCH,
        protectedBranches: cfg?.protectedBranches,
        docsAllowlist: cfg?.docsAllowlist,
      });
    } catch (e) {
      process.stderr.write(`blocked: the branch guard could not run (${e.message}).\n`);
      process.exit(2);
    }
    if (!r.allow) {
      process.stderr.write(r.reason + "\n");
      process.exit(2);
    }
    process.exit(0);
  });
}
/* v8 ignore stop */
