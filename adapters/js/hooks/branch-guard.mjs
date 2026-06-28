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

export function decide({
  filePath,
  branch,
  protectedBranches = ["main"],
  docsAllowlist = [],
}) {
  if (!protectedBranches.includes(branch)) {
    return { allow: true, reason: "not a protected branch" };
  }
  // Normalize candidate first; an upward-escaping path is never a docs match.
  const normalizedCandidate = normalizePath(filePath);
  if (normalizedCandidate.startsWith("..")) {
    return {
      allow: false,
      reason: `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.`,
    };
  }
  const isDocs = docsAllowlist.some((entry) =>
    matchesAllowlistEntry(normalizedCandidate, entry),
  );
  if (isDocs)
    return { allow: true, reason: "docs edit allowed on protected branch" };
  return {
    allow: false,
    reason: `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.`,
  };
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
  } catch {
    return false;
  }
}

// CLI wrapper: read {filePath} on stdin, branch from env, config from env JSON.
if (isMainModule()) {
  let raw = "";
  process.stdin.on("data", (d) => (raw += d));
  process.stdin.on("end", () => {
    const input = raw ? JSON.parse(raw) : {};
    const cfg = process.env.PLUMBLINE_CFG
      ? JSON.parse(process.env.PLUMBLINE_CFG)
      : {};
    const r = decide({
      ...input,
      branch: process.env.PLUMBLINE_BRANCH,
      ...cfg,
    });
    if (!r.allow) {
      process.stderr.write(r.reason + "\n");
      process.exit(2);
    }
    process.exit(0);
  });
}
