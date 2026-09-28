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

/**
 * True when `layer` occurs in `path` bounded by the start or a "/" on the left
 * and the end or a "/" on the right. A plain search, not a RegExp: a RegExp
 * built from a very long layer name hit V8's size limit and blocked where
 * the Python twin allowed (#471 review).
 */
function inPath(path, layer) {
  for (let i = path.indexOf(layer); i !== -1; i = path.indexOf(layer, i + 1)) {
    const end = i + layer.length;
    if ((i === 0 || path[i - 1] === "/") && (end === path.length || path[end] === "/")) return true;
    if (i === path.length) break;
  }
  return false;
}

function layerOf(path, layers) {
  return layers.find((l) => inPath(path, l));
}

/** The reason for an importPath that is present but not a string (#471).
 * Python twin: _IMPORT_PATH_REASON. */
const IMPORT_PATH_REASON =
  "blocked: importPath must be a string. Map the import being added into the " +
  "{filePath, importPath} stdin the boundary guard reads, or leave it out when there is none.";

export function decide({
  filePath,
  importPath,
  layers,
  direction = "downward",
}) {
  // No path to judge (an unmapped host payload) cannot be judged, so it
  // blocks (#471), as in the branch guard (#449 review).
  if (typeof filePath !== "string" || filePath === "") {
    return {
      allow: false,
      reason:
        "blocked: no file path to judge. Map the host payload's file path into the {filePath, importPath} stdin the boundary guard reads.",
    };
  }
  // Most edits add no import: with none (or an empty one) there is nothing
  // to judge (owner decision on #471). The CLI blocks an importPath that is
  // present on stdin but null.
  if (importPath == null || importPath === "") {
    return { allow: true, reason: "no import to judge" };
  }
  if (typeof importPath !== "string") {
    return { allow: false, reason: IMPORT_PATH_REASON };
  }
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
// Exercised end-to-end by the rows of adapters/hook-cases.json, which
// __tests__/hook-cases.test.mjs runs by spawning this file; v8's in-process
// instrumentation cannot see across the child process, so this glue is
// excluded from coverage rather than left falsely "uncovered".
/* v8 ignore start */

/** The only PLUMBLINE_CFG keys this guard reads (#471). */
const CFG_KEYS = ["layers", "direction"];
/**
 * PLUMBLINE_CFG is shared by the hooks (adapter-contract.md), so the branch
 * guard's keys are allowed here and left to it to validate: the mirror of the
 * branch guard's rule (owner decision on #469). The boundary guard never
 * reads them, so allowing them cannot fail open; anything neither guard reads
 * still blocks. The snake_case spellings the branch guard renames are named
 * with the key to use, as it names them.
 */
const BRANCH_KEYS = ["protectedBranches", "docsAllowlist"];
const CFG_RENAMES = {
  protected_branches: "protectedBranches",
  docs_allowlist: "docsAllowlist",
};
const DIRECTIONS = ["downward", "upward"];

/** A key as JSON, with everything outside printable ASCII escaped, so the
 * reason reads the same in the Python twin (json.dumps) whatever stderr's
 * encoding. As quoteKey in branch-guard.mjs. */
function quoteKey(k) {
  return JSON.stringify(k).replace(
    /[^\x20-\x7e]/g,
    (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"),
  );
}

/**
 * PLUMBLINE_CFG as the config decide() takes, or a reason to block (#471).
 * Unset gives the defaults (no layers, so nothing is judged; direction
 * downward); set, it must be a JSON object whose own keys are `layers`, a
 * non-empty array of non-empty strings, and `direction`, exactly "downward"
 * or "upward", plus the branch guard's keys, left unchecked (BRANCH_KEYS).
 * Anything else fails closed: an ignored `layer` typo checked no layers, and
 * any direction but "downward" was read as upward. Twin of _read_config in
 * boundary_guard.py; mirrors readConfig in branch-guard.mjs.
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
    .filter((k) => !CFG_KEYS.includes(k) && !BRANCH_KEYS.includes(k))
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
        `The boundary guard reads only "layers" and "direction"; ` +
        `"protectedBranches" and "docsAllowlist" are the branch guard's.`,
    };
  }
  if (Object.hasOwn(cfg, "layers")) {
    const { layers } = cfg;
    if (!(Array.isArray(layers) && layers.every((e) => typeof e === "string"))) {
      return { reason: "blocked: PLUMBLINE_CFG layers must be an array of strings." };
    }
    // An explicit empty list checks nothing, and an empty name matches only
    // paths with an empty segment: neither is a layering (#471).
    if (layers.length === 0) {
      return { reason: "blocked: PLUMBLINE_CFG layers must not be empty." };
    }
    if (layers.includes("")) {
      return { reason: "blocked: PLUMBLINE_CFG layers must not contain an empty entry." };
    }
  }
  if (Object.hasOwn(cfg, "direction") && !DIRECTIONS.includes(cfg.direction)) {
    return { reason: 'blocked: PLUMBLINE_CFG direction must be "downward" or "upward".' };
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

if (isMainModule()) {
  const chunks = [];
  process.stdin.on("data", (d) => chunks.push(d));
  process.stdin.on("end", () => {
    // Every failure exits 2 (#471), as in the branch guard: a Claude Code
    // hook treats only exit 2 as a block, so a crash's exit 1 would let the
    // edit through.
    let r;
    try {
      // Stdin is strict UTF-8, as in the Python twin (#471, as #475 did for
      // the branch guard): a lossy decode judged a mangled path. A byte-order
      // mark is kept, as Python keeps it.
      let raw;
      try {
        raw = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(Buffer.concat(chunks));
      } catch {
        throw new Error("stdin is not valid UTF-8");
      }
      // Empty means JSON whitespace only, as in the Python twin: trim() also
      // strips a byte-order mark, and Python's strip() also strips \x1c-\x1f.
      let parsed = {};
      if (!/^[ \t\n\r]*$/.test(raw)) {
        try {
          parsed = JSON.parse(raw);
        } catch {
          // One reason in both twins; each parser's own detail differs (#471 review).
          throw new Error("stdin is not valid JSON");
        }
      }
      // Stdin that is not an object has no filePath, so decide() blocks it.
      const input =
        parsed !== null && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
      const envReason = envProblem("PLUMBLINE_CFG");
      const { config, reason } = envReason
        ? { reason: `blocked: ${envReason}` }
        : readConfig(process.env.PLUMBLINE_CFG);
      // Only the two documented config keys, never a spread, so no config
      // key can stand in for the stdin paths (as in the branch guard).
      r = reason
        ? { allow: false, reason }
        : Object.hasOwn(input, "importPath") && typeof input.importPath !== "string"
          ? { allow: false, reason: IMPORT_PATH_REASON }
          : decide({
              filePath: input.filePath,
              importPath: input.importPath,
              layers: config.layers ?? [],
              direction: config.direction,
            });
    } catch (e) {
      process.stderr.write(`blocked: the boundary guard could not run (${e.message}).\n`);
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
