#!/usr/bin/env node
// check-bundle-sync.mjs — verify the plugin-bundled primitive copy is
// byte-identical to its primitives/ source (the single source of truth).
//
//   node scripts/check-bundle-sync.mjs
//
// The bundle at .claude-plugin/bundled/primitives/{js,python} lets a
// plugin-only user adopt the runtime with no npm/pip step. It must never
// silently drift from primitives/ — this script is the drift gate that CI
// runs on every push/PR. Exits 0 when every pair matches; exits 1 and prints
// the drifting (or missing) paths otherwise.
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const at = (p) => join(root, p);

// Explicit (source, bundled) pairs — no glob guesswork. Keep in lockstep with
// the minimal module set described in the wire-v2 bundling task: the
// dual-import-shim modules only, no tests/configs/package manifests.
const PAIRS = [
  ["primitives/js/provenance.mjs", ".claude-plugin/bundled/primitives/js/provenance.mjs"],
  ["primitives/js/audit.mjs", ".claude-plugin/bundled/primitives/js/audit.mjs"],
  ["primitives/js/marked.mjs", ".claude-plugin/bundled/primitives/js/marked.mjs"],
  ["primitives/js/index.mjs", ".claude-plugin/bundled/primitives/js/index.mjs"],
  ["primitives/python/provenance.py", ".claude-plugin/bundled/primitives/python/provenance.py"],
  ["primitives/python/audit.py", ".claude-plugin/bundled/primitives/python/audit.py"],
  ["primitives/python/marked.py", ".claude-plugin/bundled/primitives/python/marked.py"],
  ["primitives/python/__init__.py", ".claude-plugin/bundled/primitives/python/__init__.py"],
];

const drift = [];

for (const [source, bundled] of PAIRS) {
  const sourcePath = at(source);
  const bundledPath = at(bundled);

  if (!existsSync(sourcePath)) {
    drift.push(`${source}: source file missing (cannot verify bundle)`);
    continue;
  }
  if (!existsSync(bundledPath)) {
    drift.push(`${bundled}: bundle missing`);
    continue;
  }

  const sourceBytes = readFileSync(sourcePath);
  const bundledBytes = readFileSync(bundledPath);
  if (!sourceBytes.equals(bundledBytes)) {
    drift.push(`${bundled}: drifted from ${source}`);
  }
}

if (drift.length) {
  console.error("✗ bundle drift detected:");
  for (const d of drift) console.error(`    ${d}`);
  console.error("  Re-copy the affected file(s) from primitives/ into .claude-plugin/bundled/primitives/.");
  process.exit(1);
}

console.log(`✓ bundle in sync with primitives/ (${PAIRS.length} files checked)`);
