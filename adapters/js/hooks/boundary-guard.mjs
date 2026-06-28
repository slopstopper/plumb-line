// boundary-guard.mjs — block imports that violate one-way layering.

/** Escape a string so it can be used literally inside a RegExp. */
function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function layerOf(path, layers) {
  return layers.find((l) =>
    new RegExp(`(^|/)${escapeRegExp(l)}(/|$)`).test(path),
  );
}

export function decide({
  filePath,
  importPath,
  layers,
  direction = "downward",
}) {
  const from = layerOf(filePath, layers);
  const to = layerOf(importPath, layers);
  if (!from || !to || from === to)
    return { allow: true, reason: "same or unscoped layer" };
  const fromIdx = layers.indexOf(from);
  const toIdx = layers.indexOf(to);
  const ok = direction === "downward" ? toIdx > fromIdx : toIdx < fromIdx;
  return ok
    ? { allow: true, reason: `${from} -> ${to} respects ${direction}` }
    : {
        allow: false,
        reason: `boundary break: ${from} must not import ${to} (${direction})`,
      };
}

// CLI wrapper: read {filePath, importPath} on stdin, config from env JSON.
if (import.meta.url === `file://${process.argv[1]}`) {
  let raw = "";
  process.stdin.on("data", (d) => (raw += d));
  process.stdin.on("end", () => {
    const input = raw ? JSON.parse(raw) : {};
    const cfg = process.env.PLUMBLINE_CFG
      ? JSON.parse(process.env.PLUMBLINE_CFG)
      : {};
    const r = decide({
      filePath: input.filePath,
      importPath: input.importPath,
      layers: cfg.layers,
      direction: cfg.direction,
    });
    if (!r.allow) {
      process.stderr.write(r.reason + "\n");
      process.exit(2);
    }
    process.exit(0);
  });
}
