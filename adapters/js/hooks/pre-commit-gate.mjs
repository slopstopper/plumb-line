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
  for (const { name, fn } of runners) {
    const ok = await fn();
    if (!ok)
      return { allow: false, reason: `pre-commit blocked: ${name} failed` };
  }
  return { allow: true, reason: "all gates passed" };
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
  const [prog, ...args] = cmd.trim().split(/\s+/);
  let r;
  if (!prog) {
    r = { allow: false, reason: "pre-commit blocked: PLUMBLINE_TEST_CMD is not set" };
  } else {
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
