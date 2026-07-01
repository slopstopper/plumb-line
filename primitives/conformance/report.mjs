#!/usr/bin/env node
// report.mjs — run the shared conformance cases against an implementation and
// emit a pass/fail report, the envelope schema version, and a badge snippet.
// Dependency-free (no test runner). Exit code is non-zero if any case fails, so
// it doubles as a CI self-certification gate and an evidence/badge generator.
//
//   node primitives/conformance/report.mjs           # human report + badge
//   node primitives/conformance/report.mjs --badge    # badge markdown only
//   node primitives/conformance/report.mjs --json      # machine-readable result
//
// Against the JS reference implementation by default. An alternative JS
// implementation can self-certify by importing this and passing its own module.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  combineProvenance,
  auditMeta,
  validateEnvelope,
  __resetStepCounter,
  PROVENANCE_VERSION,
} from "../js/index.mjs";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const cases = JSON.parse(readFileSync(here("./cases.json"), "utf8"));

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
  return null;
}

// Shared by audit and validate: both return an issue-string list and assert on
// substring presence (or emptiness).
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

const results = [
  ...cases.combine.map((c) => ({ kind: "combine", name: c.name, error: runCombine(c) })),
  ...cases.audit.map((c) => ({ kind: "audit", name: c.name, error: runIssueList(auditMeta(c.meta), c) })),
  ...cases.validate.map((c) => ({ kind: "validate", name: c.name, error: runIssueList(validateEnvelope(c.meta), c) })),
];

const failed = results.filter((r) => r.error);
const passed = results.length - failed.length;
const ok = failed.length === 0;

const badge =
  `[![provenance: plumb-line v${PROVENANCE_VERSION}]` +
  `(https://img.shields.io/badge/provenance-plumb--line_v${PROVENANCE_VERSION}-3b82f6)]` +
  `(https://github.com/effythealien/plumb-line/blob/main/primitives/SPEC.md)`;

const mode = process.argv[2];

if (mode === "--badge") {
  console.log(badge);
  process.exit(ok ? 0 : 1);
}

if (mode === "--json") {
  console.log(
    JSON.stringify(
      { envelopeVersion: PROVENANCE_VERSION, total: results.length, passed, failed: failed.length, ok, failures: failed },
      null,
      2,
    ),
  );
  process.exit(ok ? 0 : 1);
}

console.log(`plumb-line conformance — envelope schema version ${PROVENANCE_VERSION}`);
console.log(`${passed}/${results.length} cases passed` + (ok ? "" : ` — ${failed.length} FAILED`));
for (const f of failed) console.log(`  ✗ [${f.kind}] ${f.name}: ${f.error}`);
console.log("");
console.log(ok ? "CONFORMANT. Badge snippet:" : "NOT CONFORMANT — badge withheld.");
if (ok) console.log(badge);
process.exit(ok ? 0 : 1);
