// branch-guard.mjs — block the first code edit on a protected branch.
export function decide({
  filePath,
  branch,
  protectedBranches = ["main"],
  docsAllowlist = [],
}) {
  if (!protectedBranches.includes(branch)) {
    return { allow: true, reason: "not a protected branch" };
  }
  const isDocs = docsAllowlist.some(
    (p) => filePath === p || filePath.startsWith(p),
  );
  if (isDocs)
    return { allow: true, reason: "docs edit allowed on protected branch" };
  return {
    allow: false,
    reason: `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.`,
  };
}

// CLI wrapper: read {filePath} on stdin, branch from env, config from env JSON.
if (import.meta.url === `file://${process.argv[1]}`) {
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
