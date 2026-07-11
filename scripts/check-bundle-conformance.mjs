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
import {
  combineProvenance,
  auditMeta,
  validateEnvelope,
  __resetStepCounter,
} from "../.claude-plugin/bundled/primitives/js/index.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const cases = JSON.parse(readFileSync(join(root, "primitives/conformance/cases.json"), "utf8"));

function runCombine(c) {
  __resetStepCounter();
  const out = combineProvenance(...c.inputs);
  for (const [k, v] of Object.entries(c.expect)) {
    if (JSON.stringify(out[k]) !== JSON.stringify(v))
      return `expected ${k}=${JSON.stringify(v)}, got ${JSON.stringify(out[k])}`;
  }
  for (const k of c.absent || []) {
    if (k in out) return `expected ${k} to be absent`;
  }
  if (c.expectLineageIds) {
    const ids = out.lineage.map((s) => s.id);
    if (JSON.stringify(ids) !== JSON.stringify(c.expectLineageIds))
      return `expected lineage ids ${JSON.stringify(c.expectLineageIds)}, got ${JSON.stringify(ids)}`;
  }
  return null;
}

function runIssueList(issues, c) {
  if (c.expectContains.length === 0) {
    if (issues.length !== 0) return `expected no issues, got ${JSON.stringify(issues)}`;
  } else {
    for (const needle of c.expectContains) {
      if (!issues.some((i) => i.includes(needle)))
        return `expected an issue containing "${needle}", got ${JSON.stringify(issues)}`;
    }
  }
  return null;
}

const jsResults = [
  ...cases.combine.map((c) => ({ kind: "combine", name: c.name, error: runCombine(c) })),
  ...cases.audit.map((c) => ({ kind: "audit", name: c.name, error: runIssueList(auditMeta(c.meta), c) })),
  ...cases.validate.map((c) => ({ kind: "validate", name: c.name, error: runIssueList(validateEnvelope(c.meta), c) })),
];
const jsFailed = jsResults.filter((r) => r.error);

console.log(`bundled JS: ${jsResults.length - jsFailed.length}/${jsResults.length} cases passed`);
for (const f of jsFailed) console.log(`  ✗ [${f.kind}] ${f.name}: ${f.error}`);

const ok = jsFailed.length === 0;
console.log("");
console.log(ok ? "bundle conformance (JS): CONFORMANT" : "bundle conformance (JS): NOT CONFORMANT");
process.exit(ok ? 0 : 1);
