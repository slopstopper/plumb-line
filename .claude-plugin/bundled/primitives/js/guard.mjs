// guard.mjs — the egress guard (#120, ADR-0020). auditMeta reports a problem
// after the fact; guard stops a value at an output point unless its envelope
// backs what the output claims. Fail closed: a value with no envelope, a
// malformed one, or one the audit flags is refused, and taint and confidence
// are judged from the whole lineage, not the headline fields alone.
import { CONFIDENCE, taints, weakestConfidence } from "./provenance.mjs";
import { metaOf } from "./marked.mjs";
import { auditMeta, validateEnvelope } from "./audit.mjs";

/**
 * Thrown by {@link guard} when a value may not leave through an output point.
 * `reasons` lists every reason, each prefixed with its class (`not a marked
 * value`, `invalid envelope:`, `audit:`, `mock:`, `confidence:`); the message
 * joins them after `provenance refused: `, the same in both languages.
 */
export class ProvenanceRefused extends Error {
  constructor(reasons) {
    super(`provenance refused: ${reasons.join("; ")}`);
    this.name = "ProvenanceRefused";
    this.reasons = Object.freeze([...reasons]);
  }
}

const OPTIONS = new Set(["noMock", "minConfidence"]);

/** A bad option value as a message fragment; never throws (see provenance.mjs quote). */
function quote(value) {
  if (typeof value === "number" && !Number.isFinite(value)) return String(value);
  try {
    const s = JSON.stringify(value);
    return s === undefined ? String(value) : s;
  } catch {
    return String(value);
  }
}

// A bad option is the caller's mistake, not the value's: a TypeError, raised
// before the value is looked at, so it is never mistaken for a refusal.
function readOptions(options) {
  if (options === undefined) return { noMock: true, minConfidence: "none" };
  if (options === null || typeof options !== "object" || Array.isArray(options))
    throw new TypeError(`guard: options must be an object; got ${quote(options)}`);
  for (const key of Object.keys(options)) {
    // A misspelt option would otherwise leave its check at the default.
    if (!OPTIONS.has(key)) throw new TypeError(`guard: unknown option ${key}`);
  }
  const noMock = options.noMock === undefined ? true : options.noMock;
  if (typeof noMock !== "boolean")
    throw new TypeError(`guard: the no-mock option must be a boolean; got ${quote(noMock)}`);
  const minConfidence = options.minConfidence === undefined ? "none" : options.minConfidence;
  if (!CONFIDENCE.includes(minConfidence))
    throw new TypeError(
      `guard: the minimum confidence must be one of ${CONFIDENCE.join(", ")}; got ${quote(minConfidence)}`);
  return { noMock, minConfidence };
}

// A marked value as mark() and derive() build it: a plain object holding
// `value` beside the envelope fields. A null prototype is plain too (what a
// pollution-safe JSON parser returns); metaOf copies the envelope out of it.
function isMarked(x) {
  if (x === null || typeof x !== "object" || Array.isArray(x)) return false;
  const proto = Object.getPrototypeOf(x);
  return (proto === Object.prototype || proto === null) && Object.hasOwn(x, "value");
}

/**
 * Lets a marked value through an output point only if its envelope backs it.
 * Returns the value it was given, unchanged, so an output point writes
 * `unwrap(guard(x))`; otherwise throws {@link ProvenanceRefused} listing
 * every reason.
 * @param {object} x - A value produced by mark() or derive()
 * @param {object} [options]
 * @param {boolean} [options.noMock=true] - Refuse mock taint anywhere in the
 *   envelope or its lineage. On unless turned off (P4: excluded from outputs
 *   unless explicitly opted in).
 * @param {string} [options.minConfidence="none"] - Refuse when the weakest
 *   confidence in the envelope or its lineage is below this level.
 * @returns {object} `x`
 * @throws {ProvenanceRefused} when the value may not leave
 * @throws {TypeError} when an option is unknown or has a bad value
 */
export function guard(x, options) {
  const { noMock, minConfidence } = readOptions(options);
  if (!isMarked(x)) throw new ProvenanceRefused(["not a marked value: it carries no provenance envelope"]);
  const meta = metaOf(x);
  const invalid = validateEnvelope(meta);
  if (invalid.length) throw new ProvenanceRefused(invalid.map((issue) => `invalid envelope: ${issue}`));
  // The version-legacy advisory is not a refusal: an envelope without a
  // version field is still judged on what it carries (SPEC §5b).
  const reasons = auditMeta(meta)
    .filter((issue) => !issue.startsWith("version-legacy:"))
    .map((issue) => `audit: ${issue}`);
  const steps = meta.lineage;
  if (noMock && (taints(meta) || meta.weakestSource === "mock" || steps.some((step) => taints(step))))
    reasons.push("mock: the value derives from mock data, and this output does not allow it");
  if (minConfidence !== "none") {
    const weakest = weakestConfidence(meta.confidence, ...steps.map((step) => step?.confidence));
    if (CONFIDENCE.indexOf(weakest) < CONFIDENCE.indexOf(minConfidence))
      reasons.push(`confidence: ${weakest} is below the required ${minConfidence}`);
  }
  if (reasons.length) throw new ProvenanceRefused(reasons);
  return x;
}
