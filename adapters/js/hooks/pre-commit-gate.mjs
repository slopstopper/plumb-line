// pre-commit-gate.mjs — block a commit if any runner fails.
export async function decide({ runners }) {
  for (const { name, fn } of runners) {
    const ok = await fn();
    if (!ok)
      return { allow: false, reason: `pre-commit blocked: ${name} failed` };
  }
  return { allow: true, reason: "all gates passed" };
}
