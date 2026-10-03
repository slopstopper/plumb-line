// branch-guard.mjs — block the first code edit on a protected branch.
import path from "path";
import fs from "fs";
import { spawnSync } from "child_process";
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
export function isBranchName(name) {
  if (name === "HEAD" || name.startsWith("-")) return false;
  if (BAD_REF_CHARS.test(name) || name.includes("..") || name.includes("@{") || name.endsWith(".")) {
    return false;
  }
  return name.split("/").every((c) => c !== "" && !c.startsWith(".") && !c.endsWith(".lock"));
}

/**
 * A branch name compared without case: NFC first, so an accent in decomposed
 * form is the precomposed name, as APFS reads it (#625); then upper, then
 * lower, so a letter whose lowercase is not its fold still folds (U+017F long
 * s: "maſter" is "master", as APFS reads it; toLowerCase() alone kept it).
 * Python twin: _fold.
 */
const fold = (name) => String(name).normalize("NFC").toUpperCase().toLowerCase();

/**
 * A character this runtime's Unicode does not know (general category Cn).
 * Its case mapping is unknown here, so two names cannot be shown not to fold
 * together when one of them holds one (#625). Python twin: _has_unknown.
 */
const hasUnknown = (name) => /\p{Cn}/u.test(String(name));

/**
 * The protected branch `branch` is, or null (#615). Exact, or, when git
 * ignores case (core.ignorecase), any protected name that differs only in
 * case or normalization (#625): on a case-insensitive filesystem
 * `git checkout Main` is on `main`. Where case is ignored, a character this
 * runtime does not know fails closed (#625), since a runtime with newer
 * Unicode may fold it: a branch holding one is the first protected branch
 * (after a real fold match), and a protected name holding one is matched by
 * every branch. Shared by this guard, its commit hook and the pre-commit
 * gate, so the three agree. Python twin: protected_match.
 */
export function protectedMatch(branch, protectedBranches, ignoreCase = false) {
  if (protectedBranches.includes(branch)) return branch;
  if (ignoreCase) {
    const folded = fold(branch);
    const found = protectedBranches.find((name) => fold(name) === folded)
      ?? (hasUnknown(branch) ? protectedBranches[0] : protectedBranches.find(hasUnknown));
    if (found !== undefined) return found;
  }
  return null;
}

/**
 * True when `branch` is protected only if git ignores case: the one time
 * core.ignorecase has to be read. Python twin: is_case_alias.
 */
export function isCaseAlias(branch, protectedBranches) {
  return protectedMatch(branch, protectedBranches) === null
    && protectedMatch(branch, protectedBranches, true) !== null;
}

/**
 * Whether git ignores case, from `git config --bool core.ignorecase` run in a
 * repository: exit 0 prints true or false, exit 1 means unset (git's default,
 * false). Any other answer cannot be read, so it fails closed: case is
 * ignored, and a case alias of a protected branch is protected. Python twin:
 * ignore_case_from.
 */
export function ignoreCaseFrom(status, stdout) {
  // ASCII whitespace only, as Python's bytes.strip(): a BOM or a no-break
  // space is not git's answer, so it is not read as "false".
  if (status === 0) return String(stdout).replace(/^[ \t\n\r\v\f]+|[ \t\n\r\v\f]+$/g, "") !== "false";
  return status !== 1;
}

/**
 * Whether git ignores case in the repository at `where` (default: the
 * working directory). True, failing closed, when that is not a repository or
 * git cannot be run (#615). Python twin: read_ignore_case.
 */
export function readIgnoreCase(where) {
  const opts = { cwd: where, stdio: ["ignore", "pipe", "pipe"], encoding: "utf8" };
  const repo = spawnSync("git", ["rev-parse", "--git-dir"], opts);
  if (repo.error || repo.status !== 0) return true;
  const r = spawnSync("git", ["config", "--bool", "core.ignorecase"], opts);
  if (r.error || r.status === null) return true;
  return ignoreCaseFrom(r.status, r.stdout);
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
  ignoreCase = false,
}) {
  // An unknown branch (unset, or empty as on a detached HEAD) is an
  // inconclusive result, never a pass (#449): judge the edit as if the branch
  // were protected, so only an edit allowed on every branch passes. A value
  // git would not accept as a branch name, such as `HEAD` or `main ` (#474),
  // is unknown too: it names no branch the edit could be on.
  // ignoreCase: git ignores case here, so a case alias is protected (#615).
  const unknown = isBlank(branch) || !isBranchName(String(branch));
  if (!unknown) {
    branch = protectedMatch(branch, protectedBranches, ignoreCase);
    if (branch === null) return { allow: true, reason: "not a protected branch" };
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

/** The only PLUMBLINE_CFG keys, and the snake_case spellings to rename (#469). */
const CFG_KEYS = ["protectedBranches", "docsAllowlist"];
/**
 * PLUMBLINE_CFG is shared by the hooks (adapter-contract.md), so the boundary
 * guard's keys are allowed here and left to it to validate (owner decision
 * on #469). The branch guard never reads them, so allowing them cannot fail
 * open; anything neither guard reads still blocks.
 */
const BOUNDARY_KEYS = ["layers", "direction"];
/**
 * The pre-commit gate's key, allowed and left to it to validate in the same
 * way (#613): the gate reads protectedBranches with this guard's own checks.
 */
const GATE_KEYS = ["testsOnOtherBranches"];
const CFG_RENAMES = {
  protected_branches: "protectedBranches",
  docs_allowlist: "docsAllowlist",
};

/** A key as JSON, with everything outside printable ASCII escaped, so the
 * reason reads the same in the Python twin (json.dumps) whatever stderr's
 * encoding. */
function quoteKey(k) {
  return JSON.stringify(k).replace(
    /[^\x20-\x7e]/g,
    (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"),
  );
}

/**
 * PLUMBLINE_CFG as the config decide() takes, or a reason to block (#469).
 * Unset gives the defaults; set, it must be a JSON object whose own keys are
 * the camelCase ones, each an array of strings with no empty docsAllowlist
 * entry, plus the boundary guard's keys and the pre-commit gate's, left
 * unchecked (BOUNDARY_KEYS, GATE_KEYS).
 * Anything else fails closed: an
 * ignored key (a typo, or the snake_case spelling the Python twin used to
 * accept) fell back to protecting only main. Twin of _read_config in
 * branch_guard.py.
 */
function readConfig(raw) {
  if (raw === undefined) return { config: {} };
  const retry = " Set it to a JSON object, or unset it for the defaults.";
  let cfg;
  try {
    cfg = JSON.parse(raw);
  } catch {
    return { reason: "blocked: PLUMBLINE_CFG is not valid JSON." + retry };
  }
  if (cfg === null || typeof cfg !== "object" || Array.isArray(cfg)) {
    return { reason: "blocked: PLUMBLINE_CFG is not a JSON object." + retry };
  }
  // Sorted by UTF-16 code unit, as the Python twin sorts: Object.keys puts
  // integer-like keys first, so parse order is not the same in both.
  const unknown = Object.keys(cfg)
    .filter((k) => ![...CFG_KEYS, ...BOUNDARY_KEYS, ...GATE_KEYS].includes(k))
    .sort();
  if (unknown.length > 0) {
    const named = unknown.map((k) =>
      Object.hasOwn(CFG_RENAMES, k)
        ? `${quoteKey(k)} (use ${quoteKey(CFG_RENAMES[k])})`
        : quoteKey(k),
    );
    return {
      reason:
        `blocked: PLUMBLINE_CFG has unknown key(s) ${named.join(", ")}. ` +
        `The branch guard reads only "protectedBranches" and "docsAllowlist"; ` +
        `"layers" and "direction" are the boundary guard's; ` +
        `"testsOnOtherBranches" is the pre-commit gate's.`,
    };
  }
  for (const key of CFG_KEYS) {
    if (
      Object.hasOwn(cfg, key) &&
      !(Array.isArray(cfg[key]) && cfg[key].every((e) => typeof e === "string"))
    ) {
      return { reason: `blocked: PLUMBLINE_CFG ${key} must be an array of strings.` };
    }
  }
  // decide() only meets an empty entry when it reaches it, so an earlier match
  // or an unprotected branch let the config through (#469 review).
  if (cfg.docsAllowlist?.includes("")) {
    return { reason: "blocked: PLUMBLINE_CFG docsAllowlist must not contain an empty entry." };
  }
  return { config: cfg };
}

/**
 * Why an environment variable cannot be used, or null (#501). Node replaces
 * bytes that are not UTF-8 with U+FFFD before this code sees them, so U+FFFD
 * counts as not valid, in both twins. Python twin: _env_problem.
 */
function envProblem(name) {
  const value = process.env[name];
  return value !== undefined && value.includes("\ufffd")
    ? `${name} is not valid UTF-8 (or holds U+FFFD, which invalid bytes are replaced with). Set it to UTF-8 text.`
    : null;
}

/**
 * PLUMBLINE_CFG from the environment, checked as this CLI checks it: `{ config }`
 * for decide(), or `{ reason }` to block. For a caller that judges paths itself
 * with a branch it did not read from PLUMBLINE_BRANCH: the git commit hook
 * (branch-guard-commit.mjs, #464). Python twin: config_from_env.
 */
export function configFromEnv() {
  const envReason = envProblem("PLUMBLINE_CFG");
  return envReason ? { reason: `blocked: ${envReason}` } : readConfig(process.env.PLUMBLINE_CFG);
}

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
      let input = {};
      if (!/^[ \t\n\r]*$/.test(raw)) {
        try {
          input = JSON.parse(raw);
        } catch {
          // One reason in both twins; each parser's own detail differs (#471 review).
          throw new Error("stdin is not valid JSON");
        }
      }
      const branchReason = envProblem("PLUMBLINE_BRANCH");
      const { config, reason } = branchReason
        ? { reason: `blocked: ${branchReason}` }
        : configFromEnv();
      // Only the documented config keys, never a spread: a spread let a
      // config `branch` or `filePath` override the real ones.
      // core.ignorecase is read only when it decides (#615), from the project
      // Claude Code names, else the working directory; unreadable fails closed.
      const branch = process.env.PLUMBLINE_BRANCH;
      const protectedBranches = config?.protectedBranches ?? ["main"];
      r = reason
        ? { allow: false, reason }
        : decide({
            filePath: input?.filePath,
            branch,
            protectedBranches,
            docsAllowlist: config.docsAllowlist,
            ignoreCase: typeof branch === "string" && isCaseAlias(branch, protectedBranches)
              && readIgnoreCase(process.env.CLAUDE_PROJECT_DIR || undefined),
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
