// pre-commit-gate.mjs — block a commit if any runner fails; with
// PLUMBLINE_CFG set, only on a protected branch (#613). Python twin:
// pre_commit_gate.py.
import fs from "fs";
import { fileURLToPath } from "url";

// True when this file is the process entry point, resolving symlinks on both
// sides (as branch-guard does). A plain `file://${argv[1]}` string compare
// never matched through a symlink, so a linked gate exited 0 and blocked
// nothing (v0.11.3 dogfood). Inlined, not shared: hooks are copied singly.
function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(fileURLToPath(import.meta.url)) === fs.realpathSync(process.argv[1]);
    /* v8 ignore next 3 -- defensive fail-closed on realpath error */
  } catch {
    return false;
  }
}
export async function decide({ runners }) {
  // A gate that ran nothing did not pass (#476): every way of not running the
  // tests blocks (#467), as in the Python twin. Any iterable counts, so an
  // empty generator (which has no length) blocks too. Only the first runner
  // is read to tell, so a generator is still read lazily and stops at the
  // first failure.
  const it = runners[Symbol.iterator]();
  let next = it.next();
  if (next.done) {
    return { allow: false, reason: "pre-commit blocked: no gates configured" };
  }
  for (; !next.done; next = it.next()) {
    const { name, fn } = next.value;
    const ok = await fn();
    // Only true passes (#493): any other answer is one the gate cannot read,
    // and reading it by truthiness let 1 or "ok" through. As in the Python twin.
    if (ok === false)
      return { allow: false, reason: `pre-commit blocked: ${name} failed` };
    if (ok !== true)
      return { allow: false, reason: `pre-commit blocked: ${name} returned a result that is not true or false` };
  }
  return { allow: true, reason: "all gates passed" };
}

/** What testsOnOtherBranches may be (#613); absent means "skip". */
const TESTS_ON_OTHER_BRANCHES = ["skip", "run"];

/** What the gate reads from the branch guard and its commit hook. Python twin: _GUARD_NEEDS, _COMMIT_HOOK_NEEDS. */
const GUARD_NEEDS = ["configFromEnv", "isBranchName", "protectedMatch", "isCaseAlias", "readIgnoreCase"];
const COMMIT_HOOK_NEEDS = ["resolveBranch", "GitRefused"];

/** Why the gate cannot read PLUMBLINE_CFG without them, the same in both twins. */
const CANNOT_LOAD = "pre-commit blocked: PLUMBLINE_CFG is set, and the gate reads it with the branch guard's files, "
  + "which cannot be loaded. Copy the branch guard and its commit hook, from the same release as the gate, beside it.";

/**
 * Where a commit lands, for the gate (#613), from resolveBranch() in
 * branch-guard-commit.mjs: `{ kind: "protected", branch }` (the protected
 * name), `{ kind: "unknown", why }` or `{ kind: "other", branch }`.
 * `isBranchName` is the branch guard's rule; `protectedName(branch)` the
 * protected branch a branch is, or null, as the branch guard matches it
 * (protectedMatch, #615). Judged in the commit hook's order: the branch
 * itself, then every other branch a rebase with --update-refs will move. Any
 * of them protected makes the commit protected; any of them unknown makes it
 * unknown, which the gate treats as protected. Python twin: classify_branch.
 */
export function classifyBranch({ resolved, isBranchName, protectedName }) {
  const { branch = null } = resolved;
  let { why } = resolved;
  if (why != null || branch === null || !isBranchName(branch)) {
    why ??= branch === null
      ? "HEAD is not on a branch"
      : `HEAD is on ${JSON.stringify(branch)}, which is not a branch name`;
    return { kind: "unknown", why };
  }
  if (protectedName(branch) !== null) return { kind: "protected", branch: protectedName(branch) };
  if (resolved.alsoWhy != null) return { kind: "unknown", why: resolved.alsoWhy };
  for (const other of resolved.also ?? []) {
    if (!isBranchName(other)) {
      return { kind: "unknown", why: `the rebase also moves ${JSON.stringify(other)}, which is not a branch name` };
    }
    if (protectedName(other) !== null) return { kind: "protected", branch: protectedName(other) };
  }
  return { kind: "other", branch };
}

/**
 * The gate's messages (#613), approved as text by the owner: change them only
 * with the owner's approval. Python twin: _protected_failed, _unknown_failed,
 * _skipped, _other_failed.
 */
export const MESSAGES = {
  protectedFailed: (branch) =>
    `pre-commit blocked: the tests failed, and \`${branch}\` is a protected branch. Fix the code, or ` +
    "commit on another branch (`git switch -c <name>`); there the tests can fail, and the work reaches " +
    `\`${branch}\` through review, not a local merge. Mark a test as an expected failure only if the user ` +
    "decides it should wait; mark it strict, with their reason.",
  unknownFailed: (why) =>
    `pre-commit blocked: the tests failed, and the branch is unknown (${why}), so it is treated as ` +
    "protected. Fix the code, or commit on a named branch.",
  skipped: (branch) =>
    `pre-commit: tests not run on \`${branch}\` (testsOnOtherBranches is "skip"), so this commit is ` +
    'unchecked. Set testsOnOtherBranches to "run" to run them here.',
  otherFailed: (branch) =>
    `pre-commit: the tests failed on \`${branch}\`; committed anyway (only protected branches block). ` +
    "This commit is red: say so when you report it.",
};

/**
 * Split a command into words with shell-style quoting and no shell, as the
 * Python twin's shlex.split does (#472): whitespace separates words; single
 * quotes are literal; inside double quotes a backslash escapes only `"` and
 * `\`; outside quotes it escapes any character; `#` is ordinary; an empty
 * quoted word is kept. Splitting on whitespace alone passed `""` to the
 * command as two characters, so `test -n ""` passed the gate. Throws with
 * shlex's messages, so both twins give the same reason.
 * @param {string} cmd
 * @returns {string[]}
 */
export function splitCommand(cmd) {
  const words = [];
  let word = "";
  let state = " "; // " " between words, "a" in a word, or the open quote
  for (let i = 0; i < cmd.length; i++) {
    const ch = cmd[i];
    if (state === "'") {
      if (ch === "'") state = "a";
      else word += ch;
    } else if (state === '"') {
      if (ch === '"') {
        state = "a";
      } else if (ch === "\\") {
        if (i + 1 === cmd.length) throw new Error("No escaped character");
        const next = cmd[++i];
        if (next !== '"' && next !== "\\") word += "\\";
        word += next;
      } else {
        word += ch;
      }
    } else if (" \t\r\n".includes(ch)) {
      if (state === "a") words.push(word);
      word = "";
      state = " ";
    } else {
      state = ch === "'" || ch === '"' ? ch : "a";
      if (ch === "\\") {
        if (i + 1 === cmd.length) throw new Error("No escaped character");
        word += cmd[++i];
      } else if (state === "a") {
        word += ch;
      }
    }
  }
  if (state === "'" || state === '"') throw new Error("No closing quotation");
  if (state === "a") words.push(word);
  return words;
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

// CLI wrapper: reads PLUMBLINE_TEST_CMD (and PLUMBLINE_CFG, #613) from env;
// runs the command via child_process.
// Process-entry glue (env/spawn/exit); not exercised in-process. Excluded from
// coverage — the pure decide() above is unit-tested.
/* v8 ignore start */
if (isMainModule()) {
  // Every way of not running the tests exits 2 (#467): a Claude Code hook
  // treats only exit 2 as a block, so exit 1 let the commit through. Git
  // treats any non-zero exit as a block, so nothing changes there.
  const { spawnSync } = await import("child_process");
  const cmd = process.env.PLUMBLINE_TEST_CMD ?? "";
  let r;
  let argv = [];
  const envReason = envProblem("PLUMBLINE_TEST_CMD");
  if (envReason) r = { allow: false, reason: `pre-commit blocked: ${envReason}` };
  try {
    if (!r) argv = splitCommand(cmd);
  } catch (e) {
    // An unbalanced quote or a trailing backslash: reported as the Python twin does.
    r = { allow: false, reason: `pre-commit blocked: the test command could not be run (${e.message})` };
  }
  if (!r && argv.length === 0) {
    r = { allow: false, reason: "pre-commit blocked: PLUMBLINE_TEST_CMD is not set" };
  }
  const [prog, ...args] = argv;
  const runTests = async () => {
    try {
      return await decide({
        runners: [{
          name: cmd,
          fn: () => {
            const res = spawnSync(prog, args, { stdio: "inherit" });
            // Not started: the program and Node's error code (ENOENT, EACCES),
            // as the Python twin gives the errno name.
            if (res.error) throw new Error(`${prog}: ${res.error.code ?? res.error.message}`);
            return res.status === 0;
          },
        }],
      });
    } catch (e) {
      return { allow: false, broken: true, reason: `pre-commit blocked: the test command could not be run (${e.message})` };
    }
  };
  // With no PLUMBLINE_CFG the tests run on every branch and a failure
  // blocks, as before #613, and nothing else is read. With it set the gate is
  // branch-aware: a protected or unknown branch runs the tests and blocks on
  // failure; any other branch skips them, or with testsOnOtherBranches "run"
  // runs them and only reports a failure. The test command is checked first
  // (above), so a broken one blocks even where the tests would be skipped.
  // Cases: adapters/commit-hook-cases.json.
  if (!r && process.env.PLUMBLINE_CFG === undefined) r = await runTests();
  let guard;
  let commitHook;
  if (!r) {
    // Imported only when PLUMBLINE_CFG is set, so a gate copied alone still
    // runs with it unset, as before.
    // An older release's files import, but lack what the gate reads (#613
    // review): say so, rather than fail on the first missing name.
    try {
      guard = await import("./branch-guard.mjs");
      commitHook = await import("./branch-guard-commit.mjs");
      if (!GUARD_NEEDS.every((n) => typeof guard[n] === "function")
          || !COMMIT_HOOK_NEEDS.every((n) => typeof commitHook[n] === "function")) {
        throw new Error("missing exports");
      }
    } catch {
      r = { allow: false, reason: CANNOT_LOAD };
    }
  }
  let config;
  let mode;
  if (!r) {
    const read = guard.configFromEnv();
    if (read.reason) r = { allow: false, reason: `pre-commit ${read.reason}` };
    config = read.config;
  }
  if (!r) {
    // Own key only, as the guards read keys: a null or inherited value is not "skip".
    mode = Object.hasOwn(config, "testsOnOtherBranches") ? config.testsOnOtherBranches : "skip";
    if (!TESTS_ON_OTHER_BRANCHES.includes(mode)) {
      r = { allow: false, reason: 'pre-commit blocked: PLUMBLINE_CFG testsOnOtherBranches must be "skip" or "run".' };
    }
  }
  if (!r) {
    // A branch that cannot be read is unknown, so treated as protected.
    let resolved;
    try {
      resolved = commitHook.resolveBranch();
    } catch (e) {
      resolved = {
        branch: null,
        why: e instanceof commitHook.GitRefused ? `the gate ${e.message}` : `the gate could not read the branch (${e.message})`,
      };
    }
    // core.ignorecase is read only when it decides (#615); unreadable fails closed.
    const protectedBranches = config.protectedBranches ?? ["main"];
    const named = [resolved.branch ?? null, ...(resolved.also ?? [])].filter((b) => b !== null);
    const ignoreCase = named.some((b) => guard.isCaseAlias(b, protectedBranches)) && guard.readIgnoreCase();
    const where = classifyBranch({
      resolved,
      isBranchName: guard.isBranchName,
      protectedName: (b) => guard.protectedMatch(b, protectedBranches, ignoreCase),
    });
    if (where.kind === "other" && mode === "skip") {
      r = { allow: true, notice: MESSAGES.skipped(where.branch) };
    } else {
      r = await runTests();
      if (!r.allow && !r.broken) {
        r = where.kind === "other"
          ? { allow: true, notice: MESSAGES.otherFailed(where.branch) }
          : {
              allow: false,
              reason: where.kind === "protected" ? MESSAGES.protectedFailed(where.branch) : MESSAGES.unknownFailed(where.why),
            };
      }
    }
  }
  if (!r.allow) {
    process.stderr.write(r.reason + "\n");
    process.exit(2);
  }
  if (r.notice) process.stderr.write(r.notice + "\n");
  process.exit(0);
}
/* v8 ignore stop */
