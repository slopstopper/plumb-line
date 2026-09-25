// run-cases.mjs — the one interpreter of cases.json for JS implementations.
// report.mjs (the self-certification gate) runs it against the reference
// implementation; scripts/check-bundle-conformance.mjs runs it against the
// plugin-bundled copy. One copy, so a new case field cannot be honoured by
// one and silently ignored by the other (#369). An alternative JS
// implementation self-certifies by passing its own module as `impl`.
//
// impl: { combineProvenance, auditMeta, validateEnvelope, __resetStepCounter }
// Returns one { kind, name, error } per case; error is null on a pass.
import { createHash } from "node:crypto";

// Every field a case may carry. Anything else is reported as an error, never
// skipped, so a field added to cases.json must be taught to this runner.
const KNOWN_FIELDS = {
  combine: new Set(["name", "inputs", "expect", "absent", "expectLineageIds"]),
  audit: new Set(["name", "meta", "expectContains"]),
  validate: new Set(["name", "meta", "expectContains"]),
};

function unknownFields(kind, c) {
  const extra = Object.keys(c).filter((k) => !KNOWN_FIELDS[kind].has(k));
  return extra.length ? `unknown case field(s) ${extra.join(", ")}: teach run-cases.mjs to interpret them` : null;
}

function runCombine(impl, c) {
  impl.__resetStepCounter();
  const out = impl.combineProvenance(...c.inputs);
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

const RUN = {
  combine: (impl, c) => runCombine(impl, c),
  audit: (impl, c) => runIssueList(impl.auditMeta(c.meta), c),
  validate: (impl, c) => runIssueList(impl.validateEnvelope(c.meta), c),
};

// Top-level keys of cases.json that are metadata, not case kinds.
const META_KEYS = new Set(["_doc", "version"]);

// Case-table versions this runner models. A table at another version fails
// rather than being read as if it were this one (#433).
const KNOWN_TABLE_VERSIONS = new Set([1]);

/** What a verdict was earned on: the table's version, the sha256 of its exact
 *  bytes, and the case count per kind. `bytes` is the file as read (#433). */
export function describeCaseTable(cases, bytes) {
  return {
    version: cases.version,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    counts: Object.fromEntries(Object.keys(RUN).map((kind) => [kind, (cases[kind] || []).length])),
  };
}

export function runCases(impl, cases) {
  const badVersion = KNOWN_TABLE_VERSIONS.has(cases.version) ? [] : [{
    kind: "(table)",
    name: "version",
    error: `unknown case-table version ${cases.version}: this runner models ${[...KNOWN_TABLE_VERSIONS].join(", ")}`,
  }];
  // A case kind this runner does not interpret is a failure, never a skip:
  // otherwise its cases would silently not run and the gate would still pass.
  const unknownKinds = Object.keys(cases)
    .filter((k) => !META_KEYS.has(k) && !(k in RUN))
    .map((kind) => ({ kind, name: "(whole kind)", error: `unknown case kind ${kind}: teach run-cases.mjs to interpret it` }));
  return [
    ...badVersion,
    ...Object.keys(RUN).flatMap((kind) =>
      cases[kind].map((c) => ({ kind, name: c.name, error: unknownFields(kind, c) ?? RUN[kind](impl, c) })),
    ),
    ...unknownKinds,
  ];
}
