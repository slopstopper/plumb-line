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
// Against the JS reference implementation. An alternative JS implementation
// self-certifies by passing its own module to runCases() in run-cases.mjs.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as reference from "../js/index.mjs";
import { runCases, describeCaseTable } from "./run-cases.mjs";

const { PROVENANCE_VERSION } = reference;
const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const casesBytes = readFileSync(here("./cases.json"));
const cases = JSON.parse(casesBytes.toString("utf8"));
// Which table the verdict below was earned on, so a stored verdict can be
// re-run against the same cases (#433).
const caseTable = describeCaseTable(cases, casesBytes);
const tableLine =
  `case table v${caseTable.version}, sha256:${caseTable.sha256.slice(0, 12)} (` +
  Object.entries(caseTable.counts).map(([k, n]) => `${k} ${n}`).join(", ") + ")";

// The case interpreter lives in run-cases.mjs, shared with the bundle check (#369).
const results = runCases(reference, cases);

const failed = results.filter((r) => r.error);
// A rejected table is not a case: count cases only, so an unknown table
// version reads as its own failure instead of "41/42 cases passed".
const caseResults = results.filter((r) => r.kind !== "(table)");
const passed = caseResults.filter((r) => !r.error).length;
const ok = failed.length === 0;

const badge =
  `[![provenance: plumb-line v${PROVENANCE_VERSION}]` +
  `(https://img.shields.io/badge/provenance-plumb--line_v${PROVENANCE_VERSION}-3b82f6)]` +
  `(https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md)`;

const mode = process.argv[2];

if (mode === "--badge") {
  console.log(badge);
  process.exit(ok ? 0 : 1);
}

if (mode === "--json") {
  console.log(
    JSON.stringify(
      { envelopeVersion: PROVENANCE_VERSION, caseTable, total: caseResults.length, passed, failed: failed.length, ok, failures: failed },
      null,
      2,
    ),
  );
  process.exit(ok ? 0 : 1);
}

console.log(`plumb-line conformance — envelope schema version ${PROVENANCE_VERSION}`);
console.log(tableLine);
console.log(`${passed}/${caseResults.length} cases passed` + (ok ? "" : ` — ${failed.length} FAILED`));
for (const f of failed) console.log(`  ✗ [${f.kind}] ${f.name}: ${f.error}`);
console.log("");
console.log(ok ? "CONFORMANT. Badge snippet:" : "NOT CONFORMANT — badge withheld.");
if (ok) console.log(badge);
process.exit(ok ? 0 : 1);
