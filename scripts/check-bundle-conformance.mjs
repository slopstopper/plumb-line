#!/usr/bin/env node
// check-bundle-conformance.mjs — run the shared conformance cases
// (primitives/conformance/cases.json) against the plugin-BUNDLED copy of the
// JS primitive, so a plugin-only user's vendored runtime is provably
// identical in behavior to the published package. Complements
// check-bundle-sync.mjs (byte identity of source) with a behavioral identity
// check.
//
// The Python bundle has its own runner, scripts/test_bundle_conformance.py
// (run via `python3 -m pytest -q scripts/test_bundle_conformance.py`), kept
// separate so this script has zero Python dependency and CI can run each
// language's bundle-conformance check in its own job.
//
//   node scripts/check-bundle-conformance.mjs
//
// Exits non-zero if any case fails against the bundled JS module set.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import * as bundled from "../.claude-plugin/bundled/primitives/js/index.mjs";
import { runCases } from "../primitives/conformance/run-cases.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const cases = JSON.parse(readFileSync(join(root, "primitives/conformance/cases.json"), "utf8"));

// The same interpreter report.mjs uses, so the two cannot drift (#369).
const jsResults = runCases(bundled, cases);
const jsFailed = jsResults.filter((r) => r.error);

console.log(`bundled JS: ${jsResults.length - jsFailed.length}/${jsResults.length} cases passed`);
for (const f of jsFailed) console.log(`  ✗ [${f.kind}] ${f.name}: ${f.error}`);

const ok = jsFailed.length === 0;
console.log("");
console.log(ok ? "bundle conformance (JS): CONFORMANT" : "bundle conformance (JS): NOT CONFORMANT");
process.exit(ok ? 0 : 1);
