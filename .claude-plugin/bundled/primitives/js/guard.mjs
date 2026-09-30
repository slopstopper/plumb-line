// guard.mjs — the egress guard (#120, ADR-0020). auditMeta reports a problem
// after the fact; guard stops a value at an output point unless its envelope
// backs what the output claims. Fail closed: a value with no envelope, a
// malformed one, or one the audit flags is refused, and taint and confidence
// are judged from the whole lineage, not the headline fields alone.
import { CONFIDENCE, STATUS, isScore, taints, weakestConfidence } from "./provenance.mjs";
import { metaOf } from "./marked.mjs";
import { auditMeta, validateEnvelope } from "./audit.mjs";

/**
 * Thrown by {@link guard} when a value may not leave through an output point.
 * `reasons` lists every reason, each prefixed with its class (`not a marked
 * value`, `invalid envelope:`, `audit:`, `mock:`, `confidence:`, `source:`); the message
 * joins them after `provenance refused: `, the same in both languages.
 */
export class ProvenanceRefused extends Error {
  constructor(reasons) {
    super(`provenance refused: ${reasons.join("; ")}`);
    this.name = "ProvenanceRefused";
    this.reasons = Object.freeze([...reasons]);
  }
}

const OPTIONS = ["noMock", "minConfidence", "minSource"];
// The audit's advisories about the version field that do not stop a value:
// an envelope older or newer than this library is judged on what it carries
// (SPEC §5b: a version exists to make drift legible, not to gate). A
// malformed version is not among them.
const ADVISORY = ["version-legacy:", "version-future:"];

/** A value as a message fragment. It never throws, so a malformed value the
 * guard cannot print (a BigInt in a null-prototype object, a cycle) is still
 * refused, not turned into a TypeError a caller would read as a bad option.
 * The same as provenance.mjs quote, which is not exported. */
function quote(value) {
  if (typeof value === "number" && !Number.isFinite(value)) return String(value);
  try {
    const s = JSON.stringify(value);
    return s === undefined ? String(value) : s;
  } catch {
    try {
      return String(value);
    } catch {
      try {
        // A null-prototype object has no toString either.
        return Object.prototype.toString.call(value);
      } catch {
        // A revoked Proxy, or one whose traps throw, cannot even be tagged.
        return "<unprintable>";
      }
    }
  }
}

// A plain object: what an object literal or JSON.parse builds, or a
// null-prototype object (what a pollution-safe JSON parser returns).
function isPlain(x) {
  if (x === null || typeof x !== "object" || Array.isArray(x)) return false;
  const proto = Object.getPrototypeOf(x);
  return proto === Object.prototype || proto === null;
}

// A bad option is the caller's mistake, not the value's: a TypeError, raised
// before the value is looked at, so it is never mistaken for a refusal. Only
// an own value is read, so an inherited one cannot turn a check off.
function readOptions(options) {
  if (options === undefined) return { noMock: true, minConfidence: "none", minSource: STATUS[0] };
  if (!isPlain(options)) throw new TypeError(`guard: options must be a plain object; got ${quote(options)}`);
  const unknown = Object.keys(options).filter((key) => !OPTIONS.includes(key));
  // A misspelt option would otherwise leave its check at the default.
  if (unknown.length) throw new TypeError(`guard: unknown option ${unknown.join(", ")}`);
  const own = (key, fallback) =>
    (Object.hasOwn(options, key) && options[key] !== undefined ? options[key] : fallback);
  const noMock = own("noMock", true);
  if (typeof noMock !== "boolean")
    throw new TypeError(`guard: the no-mock option must be a boolean; got ${quote(noMock)}`);
  const minConfidence = own("minConfidence", "none");
  if (!CONFIDENCE.includes(minConfidence))
    throw new TypeError(
      `guard: the minimum confidence must be one of ${CONFIDENCE.join(", ")}; got ${quote(minConfidence)}`);
  const minSource = own("minSource", STATUS[0]);
  if (!STATUS.includes(minSource))
    throw new TypeError(`guard: the minimum source must be one of ${STATUS.join(", ")}; got ${quote(minSource)}`);
  return { noMock, minConfidence, minSource };
}

// What the guard cannot read on the ladders is malformed (SPEC §5c). The
// constructors refuse an off-ladder source or confidence (ADR-0019) and drop
// an invalid score; the law tolerates all of these in a handed envelope, and
// an output point fails closed.
function unreadable(meta) {
  const issues = [];
  if (!STATUS.includes(meta.source)) issues.push(`source ${quote(meta.source)} is not on the source ladder`);
  if (!CONFIDENCE.includes(meta.confidence))
    issues.push(`confidence ${quote(meta.confidence)} is not on the confidence ladder`);
  if ("weakestSource" in meta && !STATUS.includes(meta.weakestSource))
    issues.push(`weakestSource ${quote(meta.weakestSource)} is not on the source ladder`);
  if ("confidenceScore" in meta && !isScore(meta.confidenceScore))
    issues.push(`confidenceScore ${quote(meta.confidenceScore)} is not a number in [0, 1]`);
  meta.lineage.forEach((step, i) => {
    // A plain object, as derive() builds it: a Map or class instance could
    // carry taint the field reads below would not see.
    if (!isPlain(step)) {
      issues.push(`lineage step ${i} is not a plain object`);
      return;
    }
    // A step with no source is refused (#525 review): a missing confidence
    // counts as none, the weakest rung, but a source has no rung the guard
    // could degrade it to and still judge, so it cannot be shown not to be
    // mock. Combine always writes a source, null when its input had none.
    if (!("source" in step)) issues.push(`lineage step ${i} has no source`);
    else if (!STATUS.includes(step.source))
      issues.push(`lineage step ${i} source ${quote(step.source)} is not on the source ladder`);
    if ("confidence" in step && !CONFIDENCE.includes(step.confidence))
      issues.push(`lineage step ${i} confidence ${quote(step.confidence)} is not on the confidence ladder`);
    if ("derivedFromMock" in step && typeof step.derivedFromMock !== "boolean")
      issues.push(`lineage step ${i} derivedFromMock must be a boolean`);
    // The audit skips a score it cannot read, so a bad one could hide an
    // over-claim against a readable top-level score.
    if ("confidenceScore" in step && !isScore(step.confidenceScore))
      issues.push(`lineage step ${i} confidenceScore ${quote(step.confidenceScore)} is not a number in [0, 1]`);
  });
  return issues;
}

// An array copied by index, so a hole is the undefined it reads as, as Python's
// None step is (#560 review): every, some, forEach, reduce and flatMap skip
// holes. A plain loop, because Array.from follows an iterator: the array's
// own, or one polluted onto a prototype, which could cut the copy short.
function byIndex(a) {
  const out = new Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = a[i];
  return out;
}

/**
 * Lets a marked value through an output point only if its envelope backs it.
 * Returns the value it was given, unchanged, so an output point writes
 * `unwrap(guard(x))`; otherwise throws {@link ProvenanceRefused} listing
 * every reason.
 * @param {object} x - A value produced by mark() or derive()
 * @param {object} [options]
 * @param {boolean} [options.noMock=true] - Refuse mock taint anywhere in the
 *   envelope or its lineage. On unless turned off (Principle 4's mock clause:
 *   excluded from outputs unless explicitly opted in).
 * @param {string} [options.minConfidence="none"] - Refuse when the weakest
 *   confidence in the envelope or its lineage is below this level.
 * @param {string} [options.minSource="unavailable"] - Refuse when the weakest
 *   source the ancestry shows (the headline, weakestSource and every lineage
 *   step, skipping the law's own label "derived") is below this rung. Off by
 *   default, by the owner's decision (#541): refuses fallback and
 *   inferred data without a mock label; assumes a complete lineage.
 * @returns {object} `x`
 * @throws {ProvenanceRefused} when the value may not leave
 * @throws {TypeError} when the options are not a plain object, or one is
 *   unknown or has a bad value
 */
export function guard(x, options) {
  const { noMock, minConfidence, minSource } = readOptions(options);
  // A marked value as mark() and derive() build it: a plain object holding
  // `value` beside the envelope fields.
  if (!isPlain(x) || !Object.hasOwn(x, "value"))
    throw new ProvenanceRefused(["not a marked value: it carries no provenance envelope"]);
  // The value's own envelope fields only. The structural and ladder checks
  // read top-level fields with `in`, so they are handed a null-prototype
  // copy: an inherited field (a polluted prototype) cannot count as present.
  // The audit wants a plain object, and reads a polluted prototype as any
  // plain-object reader does (the threat model's in-process attacker).
  const own = Object.fromEntries(Object.entries(metaOf(x)).filter(([key]) => Object.hasOwn(x, key)));
  // The lineage is copied once, by index, and that copy is what is both
  // validated and judged, as Python rebuilds meta['lineage'] once (#560
  // review): a hole is refused as a step that is not a plain object.
  if (Array.isArray(own.lineage)) own.lineage = byIndex(own.lineage);
  const meta = { ...own };
  const bare = Object.assign(Object.create(null), own);
  const invalid = validateEnvelope(bare);
  const malformed = invalid.length ? invalid : unreadable(bare);
  if (malformed.length) throw new ProvenanceRefused(malformed.map((issue) => `invalid envelope: ${issue}`));
  const reasons = auditMeta(meta)
    .filter((issue) => !ADVISORY.some((prefix) => issue.startsWith(prefix)))
    .map((issue) => `audit: ${issue}`);
  const steps = meta.lineage;
  if (noMock && (taints(meta) || meta.weakestSource === "mock" || steps.some((step) => taints(step))))
    reasons.push("mock: the value derives from mock data, and this output does not allow it");
  if (minConfidence !== "none") {
    // An absent step confidence counts as none: the guard vouches only for
    // what the lineage states.
    // Folded, not spread, so a long lineage cannot overflow the stack (#560).
    const weakest = steps.reduce((w, step) => weakestConfidence(w, step.confidence),
      weakestConfidence(meta.confidence));
    if (CONFIDENCE.indexOf(weakest) < CONFIDENCE.indexOf(minConfidence))
      reasons.push(`confidence: ${weakest} is below the required ${minConfidence}`);
  }
  if (minSource !== STATUS[0]) {
    // The rest of Principle 4 beside its mock clause (#541): the weakest
    // source the ancestry shows, from the headline, weakestSource and every
    // step. "derived" is the law's own label for a computed value, not a
    // source of data, so it is skipped: a derived value is judged by what it
    // was computed from. Every step here has a source on the ladder (a step
    // without one was refused above as invalid).
    const sources = [meta.source, meta.weakestSource, ...steps.map((step) => step.source)]
      .filter((source) => STATUS.includes(source) && source !== "derived");
    const weakest = sources.length ? sources.reduce((a, b) => (STATUS.indexOf(b) < STATUS.indexOf(a) ? b : a)) : undefined;
    if (weakest === undefined)
      reasons.push(`source: no source in the ancestry shows it meets the required ${minSource}`);
    else if (STATUS.indexOf(weakest) < STATUS.indexOf(minSource))
      reasons.push(`source: ${weakest} is below the required ${minSource}`);
  }
  if (reasons.length) throw new ProvenanceRefused(reasons);
  return x;
}
