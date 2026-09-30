// run-cases.mjs — the one interpreter of cases.json for JS implementations.
// report.mjs (the self-certification gate) runs it against the reference
// implementation; scripts/check-bundle-conformance.mjs runs it against the
// plugin-bundled copy. One copy, so a new case field cannot be honoured by
// one and silently ignored by the other (#369). An alternative JS
// implementation self-certifies by passing its own module as `impl`.
//
// impl: { combineProvenance, makeMeta, mark, derive, auditMeta,
//         validateEnvelope, guard, ProvenanceRefused, __resetStepCounter }
// Returns one { kind, name, error } per case; error is null on a pass.
import { createHash } from "node:crypto";
// Deep equality, as the Python runners' `==` has always been: JSON text
// comparison depended on key order and read NaN as null.
import { isDeepStrictEqual } from "node:util";

// Every field a case may carry. Anything else is reported as an error, never
// skipped, so a field added to cases.json must be taught to this runner.
const KNOWN_FIELDS = {
  combine: new Set(["name", "inputs", "expect", "absent", "expectLineageIds", "expectLineage"]),
  audit: new Set(["name", "meta", "expectContains"]),
  validate: new Set(["name", "meta", "expectContains"]),
  construct: new Set(["name", "input", "expect", "expectError", "absent"]),
  derive: new Set(["name", "inputs", "override", "expect", "expectError", "absent"]),
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
    // A prior step that is not an object has no id: null, as in the Python runners.
    const ids = out.lineage.map((s) => (s !== null && typeof s === "object" && !Array.isArray(s) ? (s.id ?? null) : null));
    if (!isDeepStrictEqual(ids, c.expectLineageIds))
      return `expected lineage ids ${JSON.stringify(c.expectLineageIds)}, got ${JSON.stringify(ids)}`;
  }
  // The whole lineage, camelCase, compared strictly: a key the step should
  // leave off must be absent, not undefined (#525).
  if (c.expectLineage) {
    const plain = JSON.parse(JSON.stringify(out.lineage, (k, v) => (v === undefined ? "<undefined>" : v)));
    if (!isDeepStrictEqual(plain, c.expectLineage))
      return `expected lineage ${JSON.stringify(c.expectLineage)}, got ${JSON.stringify(plain)}`;
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
// The shape of a construct or derive row: exactly one expectation, since a row
// with neither would check nothing and one with both would silently ignore
// `expect` (#443 review); and `absent`, a list of field names, only beside
// `expect`, where it can be checked (#566 review).
function shapeProblem(kind, c) {
  if (("expect" in c) === ("expectError" in c))
    return `a ${kind} case needs exactly one of expect or expectError`;
  if ("absent" in c && !(Array.isArray(c.absent) && c.absent.every((k) => typeof k === "string")))
    return "absent must be a list of field names";
  if ("absent" in c && !("expect" in c)) return "absent applies only to an expect case";
  if (kind === "derive") {
    if (!Array.isArray(c.inputs)) return "a derive case needs a list of inputs";
    if ("override" in c && (c.override === null || typeof c.override !== "object" || Array.isArray(c.override)))
      return "a derive case's override must be an object";
  }
  return null;
}

// The envelope a construct or derive row expects: each `expect` field equal,
// each `absent` field not written at all (JSON cannot say `undefined`, and
// `null` is a value, #566).
function envelopeProblem(out, c) {
  for (const [k, v] of Object.entries(c.expect)) {
    if (!isDeepStrictEqual(out[k], v))
      return `expected ${k}=${JSON.stringify(v)}, got ${JSON.stringify(out[k])}`;
  }
  for (const k of c.absent || []) {
    if (Object.hasOwn(out, k)) return `expected ${k} to be absent`;
  }
  return null;
}

// A derive row (#566): each input is marked with its `inputs` fields, then
// derive runs a constant function over them with `override`. The function's
// value is not under test; the envelope is.
function runDerive(impl, c) {
  const shape = shapeProblem("derive", c);
  if (shape) return shape;
  impl.__resetStepCounter();
  // The inputs are marked outside the try that judges expectError, as the
  // Python runner does: a row is about derive, so a mark that throws the
  // expected words must fail it, not pass it (v0.12.0 dogfood).
  let items;
  try {
    items = c.inputs.map((fields, i) => impl.mark(i, fields));
  } catch (e) {
    return `marking the inputs failed: ${describeThrown(e)}`;
  }
  let out;
  try {
    out = impl.derive(items, () => 0, c.override || {});
  } catch (e) {
    if (c.expectError === undefined) return `expected an envelope, got an error: ${describeThrown(e)}`;
    const message = describeThrown(e);
    return message.includes(c.expectError)
      ? null
      : `expected an error containing "${c.expectError}", got "${message}"`;
  }
  if (c.expectError !== undefined) return `expected an error containing "${c.expectError}", got an envelope`;
  return envelopeProblem(out, c);
}

function runConstruct(impl, c) {
  const shape = shapeProblem("construct", c);
  if (shape) return shape;
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
  return envelopeProblem(out, c);
}

// A thrown value as text, for a failure message; never throws, whatever the
// implementation under test threw (a Symbol message, a throwing getter).
function describeThrown(e) {
  try {
    return String(e?.message);
  } catch {
    return "a value the runner cannot print";
  }
}

// The egress guard (#120). A row's `meta` becomes a marked value (`value`
// plus the envelope fields, as mark() builds it); a non-object `meta` is
// passed as is, to pin that a value with no envelope is refused. A refusal
// is a ProvenanceRefused carrying `reasons`; any other throw is a programmer
// error (a bad option), which only an expectError row accepts, and which
// must be a TypeError (SPEC §5c).
function runGuard(impl, c) {
  const expectations = ["expectPass", "expectRefused", "expectError"].filter((k) => k in c);
  if (expectations.length !== 1)
    return "a guard case needs exactly one of expectPass, expectRefused or expectError";
  if ("expectAbsent" in c && !("expectRefused" in c))
    return "expectAbsent is read only beside expectRefused";
  // A value that could only mislead: `expectPass: false` or an empty needle
  // list would otherwise be read as a pass, or as any refusal at all.
  if ("expectPass" in c && c.expectPass !== true) return "expectPass must be true";
  for (const key of ["expectRefused", "expectAbsent"]) {
    if (key in c && !(Array.isArray(c[key]) && c[key].length)) return `${key} must list at least one reason`;
  }
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
    // Whatever was thrown, judging it must fail the row, never the run.
    try {
      return judgeGuardThrow(impl, c, e);
    } catch {
      return "the implementation threw a value the runner cannot inspect";
    }
  }
  if (!("expectPass" in c))
    return `expected ${"expectRefused" in c ? "a refusal" : "a programmer error"}, got a pass`;
  return out === x ? null : "a pass must return the marked value it was given";
}

// What a guard row makes of a thrown value: a refusal, a programmer error, or
// a wrong kind of throw. Called inside a try, so it may read the value freely.
function judgeGuardThrow(impl, c, e) {
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
    return `expected ${"expectPass" in c ? "a pass" : "a refusal"}, got an error: ${describeThrown(e)}`;
  // SPEC §5c: a bad option's error type is neither the refusal's type nor a
  // supertype of it, so a catch for one can never catch the other.
  // Judged on the prototype chain, not `constructor` (which a thrown value
  // may lack or fake), so an odd throw fails the row instead of the run.
  const proto = e !== null && typeof e === "object" ? Object.getPrototypeOf(e) : null;
  if (proto !== null && Object.prototype.isPrototypeOf.call(proto, impl.ProvenanceRefused.prototype))
    return "a bad option's error must not be a supertype of the refusal";
  // SPEC §5c and ADR-0020: a bad option is a TypeError in JS and Python;
  // the Python runner requires one, and this runner accepted any other
  // error until the v0.12.0 dogfood audit found it. Judged against this
  // runner's realm: a TypeError made in another realm (vm.runInNewContext)
  // fails, as the implementation under test runs in this one.
  if (proto === null || !(proto === TypeError.prototype || Object.prototype.isPrototypeOf.call(TypeError.prototype, proto))) {
    let kind = "a value with no constructor name";
    try {
      const name = proto && Object.getOwnPropertyDescriptor(proto, "constructor")?.value?.name;
      if (typeof name === "string" && name) kind = `a ${name}`;
    } catch {
      kind = "a value that cannot be inspected";
    }
    return `a bad option's error must be a TypeError (SPEC §5c), got ${kind}: ${describeThrown(e)}`;
  }
  const message = describeThrown(e);
  return message.includes(c.expectError)
    ? null
    : `expected an error containing "${c.expectError}", got "${message}"`;
}

const RUN = {
  combine: (impl, c) => runCombine(impl, c),
  construct: (impl, c) => runConstruct(impl, c),
  derive: (impl, c) => runDerive(impl, c),
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
