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

function blocked(filePath, branch, unknown) {
  return {
    allow: false,
    reason: unknown
      ? `blocked: code edit to ${filePath} with the branch unknown (PLUMBLINE_BRANCH is unset or empty). Set it to the current branch.`
      : `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.`,
  };
}

export function decide({
  filePath,
  branch,
  protectedBranches = ["main"],
  docsAllowlist = [],
}) {
  // An unknown branch (unset, or empty as on a detached HEAD) is an
  // inconclusive result, never a pass (#449): judge the edit as if the branch
  // were protected, so only an edit allowed on every branch passes. Blank
  // means ASCII whitespace, as in the Python twin.
  const unknown = branch == null || !/[^ \t\n\r\f\v]/.test(String(branch));
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
// Exercised end-to-end by the spawn-based "branch-guard CLI" tests below; v8's
// in-process instrumentation cannot see across the child process, so this glue
// is excluded from coverage rather than left falsely "uncovered".
/* v8 ignore start */
if (isMainModule()) {
  let raw = "";
  process.stdin.on("data", (d) => (raw += d));
  process.stdin.on("end", () => {
    // Every failure exits 2 (#449 review): a Claude Code hook treats only
    // exit 2 as a block, so a crash's exit 1 would let the edit through.
    let r;
    try {
      const input = raw.trim() ? JSON.parse(raw) : {};
      const cfg = process.env.PLUMBLINE_CFG
        ? JSON.parse(process.env.PLUMBLINE_CFG)
        : {};
      r = decide({
        filePath: input?.filePath,
        branch: process.env.PLUMBLINE_BRANCH,
        ...cfg,
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
