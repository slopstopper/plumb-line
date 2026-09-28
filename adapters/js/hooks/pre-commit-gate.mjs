// pre-commit-gate.mjs — block a commit if any runner fails.
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
    if (!ok)
      return { allow: false, reason: `pre-commit blocked: ${name} failed` };
  }
  return { allow: true, reason: "all gates passed" };
}

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

// CLI wrapper: reads PLUMBLINE_TEST_CMD from env; runs it via child_process.
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
  try {
    argv = splitCommand(cmd);
  } catch (e) {
    // An unbalanced quote or a trailing backslash: reported as the Python twin does.
    r = { allow: false, reason: `pre-commit blocked: the test command could not be run (${e.message})` };
  }
  if (!r && argv.length === 0) {
    r = { allow: false, reason: "pre-commit blocked: PLUMBLINE_TEST_CMD is not set" };
  }
  if (!r) {
    const [prog, ...args] = argv;
    try {
      r = await decide({
        runners: [{
          name: cmd,
          fn: () => {
            const res = spawnSync(prog, args, { stdio: "inherit" });
            if (res.error) throw res.error; // not started: say so, as the Python twin does
            return res.status === 0;
          },
        }],
      });
    } catch (e) {
      r = { allow: false, reason: `pre-commit blocked: the test command could not be run (${e.message})` };
    }
  }
  if (!r.allow) {
    process.stderr.write(r.reason + "\n");
    process.exit(2);
  }
  process.exit(0);
}
/* v8 ignore stop */
