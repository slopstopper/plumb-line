// boundary-guard.mjs — block imports that violate one-way layering.
import fs from "fs";
import { fileURLToPath } from "url";

// True when this file is the process entry point, resolving symlinks on both
// sides (as branch-guard does). A plain `file://${argv[1]}` string compare
// never matched through a symlink, so a linked hook exited 0 and blocked
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
// Process-entry glue (argv/stdin/exit); exercised via the shipped ESLint
// boundary template's integration test, not in-process. Excluded from coverage.
/* v8 ignore start */
if (isMainModule()) {
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
/* v8 ignore stop */
