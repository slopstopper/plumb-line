// pre-commit-gate.mjs — block a commit if any runner fails.
export async function decide({ runners }) {
  for (const { name, fn } of runners) {
    const ok = await fn();
    if (!ok)
      return { allow: false, reason: `pre-commit blocked: ${name} failed` };
  }
  return { allow: true, reason: "all gates passed" };
}

// CLI wrapper: reads PLUMBLINE_TEST_CMD from env; runs it via child_process.
if (import.meta.url === `file://${process.argv[1]}`) {
  const { spawnSync } = await import("child_process");
  const cmd = process.env.PLUMBLINE_TEST_CMD;
  if (!cmd) {
    process.stderr.write("PLUMBLINE_TEST_CMD not set\n");
    process.exit(1);
  }
  const [prog, ...args] = cmd.split(/\s+/);
  const runner = {
    name: cmd,
    fn: () => {
      const result = spawnSync(prog, args, { stdio: "inherit" });
      return result.status === 0;
    },
  };
  const r = await decide({ runners: [runner] });
  if (!r.allow) {
    process.stderr.write(r.reason + "\n");
    process.exit(2);
  }
  process.exit(0);
}
