// run-cases.mjs — the one interpreter of cases.json for JS implementations.
// report.mjs (the self-certification gate) runs it against the reference
// implementation; scripts/check-bundle-conformance.mjs runs it against the
// plugin-bundled copy. One copy, so a new case field cannot be honoured by
// one and silently ignored by the other (#369). An alternative JS
// implementation self-certifies by passing its own module as `impl`.
//
// impl: { combineProvenance, makeMeta, auditMeta, validateEnvelope, guard,
//         ProvenanceRefused, __resetStepCounter }
// Returns one { kind, name, error } per case; error is null on a pass.
import { createHash } from "node:crypto";
// Deep equality, as the Python runners' `==` has always been: JSON text
// comparison depended on key order and read NaN as null.
import { isDeepStrictEqual } from "node:util";

// Every field a case may carry. Anything else is reported as an error, never
// skipped, so a field added to cases.json must be taught to this runner.
const KNOWN_FIELDS = {
  combine: new Set(["name", "inputs", "expect", "absent", "expectLineageIds"]),
  audit: new Set(["name", "meta", "expectContains"]),
  validate: new Set(["name", "meta", "expectContains"]),
  construct: new Set(["name", "input", "expect", "expectError"]),
  guard: new Set(["name", "meta", "options", "expectPass", "expectRefused", "expectAbsent", "expectError"]),
};

function unknownFields(kind, c) {
  const extra = Object.keys(c).filter((k) => !KNOWN_FIELDS[kind].has(k));
  return extra.length ? `unknown case field(s) ${extra.join(", ")}: teach run-cases.mjs to interpret them` : null;
}

function runCombine(impl, c) {
  impl.__resetStepCounter();
  const out = impl.combineProvenance(...c.inputs);
  for (const [k, v] of Object.entries(c.expect)) {
    if (!isDeepStrictEqual(out[k], v))
      return `expected ${k}=${JSON.stringify(v)}, got ${JSON.stringify(out[k])}`;
  }
  for (const k of c.absent || []) {
    if (k in out) return `expected ${k} to be absent`;
  }
  if (c.expectLineageIds) {
    const ids = out.lineage.map((s) => s.id);
    if (!isDeepStrictEqual(ids, c.expectLineageIds))
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

// What makeMeta accepts and refuses (#443). A refusal throws; the case pins a
// substring of the message, whose prefix both languages word identically.
function runConstruct(impl, c) {
  // Exactly one expectation: a row with neither would check nothing, and one
  // with both would silently ignore `expect` (#443 review).
  if (("expect" in c) === ("expectError" in c))
    return "a construct case needs exactly one of expect or expectError";
  let out;
  try {
    out = impl.makeMeta(c.input);
  } catch (e) {
    if (c.expectError === undefined) return `expected an envelope, got an error: ${e.message}`;
    return String(e.message).includes(c.expectError)
      ? null
      : `expected an error containing "${c.expectError}", got "${e.message}"`;
  }
  if (c.expectError !== undefined) return `expected an error containing "${c.expectError}", got an envelope`;
  for (const [k, v] of Object.entries(c.expect)) {
    if (!isDeepStrictEqual(out[k], v))
      return `expected ${k}=${JSON.stringify(v)}, got ${JSON.stringify(out[k])}`;
  }
  return null;
}

// The egress guard (#120). A row's `meta` becomes a marked value (`value`
// plus the envelope fields, as mark() builds it); a non-object `meta` is
// passed as is, to pin that a value with no envelope is refused. A refusal
// is a ProvenanceRefused carrying `reasons`; any other throw is a programmer
// error (a bad option), which only an expectError row accepts.
function runGuard(impl, c) {
  const expectations = ["expectPass", "expectRefused", "expectError"].filter((k) => k in c);
  if (expectations.length !== 1)
    return "a guard case needs exactly one of expectPass, expectRefused or expectError";
  if ("expectAbsent" in c && !("expectRefused" in c))
    return "expectAbsent is read only beside expectRefused";
  // A value that could only mislead: `expectPass: false` or an empty needle
  // list would otherwise be read as a pass, or as any refusal at all.
  if ("expectPass" in c && c.expectPass !== true) return "expectPass must be true";
  if ("expectRefused" in c && !(Array.isArray(c.expectRefused) && c.expectRefused.length))
    return "expectRefused must list at least one reason";
  // An empty needle is in every string, so it would pin nothing.
  const needles = [...(c.expectRefused || []), ...(c.expectAbsent || []), ...("expectError" in c ? [c.expectError] : [])];
  if (needles.some((n) => typeof n !== "string" || n === ""))
    return "every expected reason or error text must be a non-empty string";
  const plain = c.meta !== null && typeof c.meta === "object" && !Array.isArray(c.meta);
  const x = plain ? { value: 1, ...c.meta } : c.meta;
  let out;
  try {
    out = "options" in c ? impl.guard(x, c.options) : impl.guard(x);
  } catch (e) {
    // An implementation without the export fails the row instead of the run.
    if (typeof impl.ProvenanceRefused !== "function")
      return "the implementation exports no ProvenanceRefused";
    if (e instanceof impl.ProvenanceRefused) {
      const reasons = e.reasons;
      if (!Array.isArray(reasons) || !reasons.every((r) => typeof r === "string"))
        return `a refusal must carry reasons as a list of strings, got ${JSON.stringify(reasons)}`;
      if (!("expectRefused" in c))
        return `expected ${"expectPass" in c ? "a pass" : "a programmer error"}, got a refusal: ${JSON.stringify(reasons)}`;
      const missing = runIssueList(reasons, { expectContains: c.expectRefused });
      if (missing) return missing;
      for (const needle of c.expectAbsent || []) {
        if (reasons.some((r) => r.includes(needle)))
          return `expected no reason containing "${needle}", got ${JSON.stringify(reasons)}`;
      }
      return null;
    }
    if (!("expectError" in c))
      return `expected ${"expectPass" in c ? "a pass" : "a refusal"}, got an error: ${e?.message}`;
    // SPEC §5c: a bad option's error type is neither the refusal's type nor a
    // supertype of it, so a catch for one can never catch the other.
    if (e !== null && typeof e === "object" && impl.ProvenanceRefused.prototype instanceof e.constructor)
      return `a bad option's error must not be a supertype of the refusal, got ${e.constructor.name}`;
    return String(e?.message).includes(c.expectError)
      ? null
      : `expected an error containing "${c.expectError}", got "${e.message}"`;
  }
  if (!("expectPass" in c))
    return `expected ${"expectRefused" in c ? "a refusal" : "a programmer error"}, got a pass`;
  return out === x ? null : "a pass must return the marked value it was given";
}

const RUN = {
  combine: (impl, c) => runCombine(impl, c),
  construct: (impl, c) => runConstruct(impl, c),
  audit: (impl, c) => runIssueList(impl.auditMeta(c.meta), c),
  validate: (impl, c) => runIssueList(impl.validateEnvelope(c.meta), c),
  guard: (impl, c) => runGuard(impl, c),
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
      Array.isArray(cases[kind])
        ? cases[kind].map((c) => ({ kind, name: c.name, error: unknownFields(kind, c) ?? RUN[kind](impl, c) }))
        // A kind the runner models but the table lacks is a failure too: a
        // table with a kind deleted must not certify (#443 review).
        : [{ kind, name: "(whole kind)", error: kind in cases
            ? `case kind ${kind} is not a list of cases`
            : `case kind ${kind} is missing from the table` }],
    ),
    ...unknownKinds,
  ];
}
