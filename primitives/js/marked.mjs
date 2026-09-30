// marked.mjs — thin wrapper sugar over the provenance law. The law lives in provenance.mjs.
import { combineProvenance, makeMeta } from "./provenance.mjs";

const META_KEYS = [
  "provenanceVersion",
  "source",
  "confidence",
  "confidenceScore",
  "derivedFromMock",
  "lineage",
  "weakestSource",
  "basis",
  "adapter",
];

// Only these keys may be supplied as overrides to derive(). lineage and
// weakestSource always come from the computed combineProvenance result;
// derivedFromMock taint cannot be cleared through an override.
const OVERRIDE_KEYS = ["source", "confidence", "confidenceScore", "basis", "adapter"];
// The override keys with no required value, for which null means unset (#566).
const OPTIONAL_OVERRIDE_KEYS = ["confidenceScore", "basis", "adapter"];

/**
 * Wraps a value with provenance metadata, producing a marked value object.
 * The returned object is frozen; its `value` property holds the original value
 * and the remaining properties are the metadata envelope fields.
 * @param {*} value - Any value to track
 * @param {object} metaInput - Initial metadata; same options as {@link makeMeta},
 *   and `source` is required (#177)
 * @returns {Readonly<{value: *, source: string, confidence: string, derivedFromMock: boolean, lineage: object[]}>}
 */
export function mark(value, metaInput = {}) {
  return Object.freeze({ value, ...makeMeta(metaInput) });
}

/**
 * Extracts the raw value from a marked object.
 * @param {object} marked - A value produced by {@link mark} or {@link derive}
 * @returns {*} The unwrapped value
 */
export function unwrap(marked) {
  return marked?.value;
}

/**
 * Extracts the provenance metadata from a marked object as a plain object.
 * Only the known envelope keys are included; the `value` field is excluded.
 * @param {object} marked - A value produced by {@link mark} or {@link derive}
 * @returns {object} Metadata envelope
 */
export function metaOf(marked) {
  const meta = {};
  for (const key of META_KEYS)
    if (key in (marked || {})) meta[key] = marked[key];
  return meta;
}

/** A plain (object-literal or null-prototype) object holding `value`: the
 * shape mark() and derive() build, and the one guard() reads (#550). */
function isMarkedValue(x) {
  if (x === null || typeof x !== "object" || Array.isArray(x)) return false;
  const proto = Object.getPrototypeOf(x);
  return (proto === Object.prototype || proto === null) && Object.hasOwn(x, "value");
}

/**
 * Derives a new marked value from one or more marked inputs.
 * The combination law is applied automatically: mock taint and the weakest
 * confidence propagate to the result and cannot be overridden.
 * @param {object[]} inputs - Marked values produced by {@link mark} or {@link derive}
 * @param {Function} fn - Pure function applied to the unwrapped input values
 * @param {object} [metaOverride={}] - Optional overrides for `source`, `confidence`,
 *   `confidenceScore`, `basis`, or `adapter`; `derivedFromMock` cannot be cleared.
 *   By convention `basis` is an operation label naming the transform `fn`
 *   (e.g. `"pricing.applyFx@v3"`) — lineage records input states, not `fn`. See SPEC §4.
 * @returns {Readonly<{value: *, source: string, confidence: string, derivedFromMock: boolean, lineage: object[]}>}
 */
export function derive(inputs, fn, metaOverride = {}) {
  // The inputs are read once, into an array (#550 review): a generator was
  // otherwise used up by the check and combined as zero inputs, dropping its
  // taint, and forEach skipped a sparse array's holes. A string or a
  // non-iterable is not a list of inputs.
  if (inputs == null || typeof inputs === "string" || typeof inputs[Symbol.iterator] !== "function")
    throw new TypeError("derive: inputs must be a list of marked values");
  const items = Array.from(inputs);
  // Every input must be a marked value, as the egress guard reads one: a plain
  // object holding `value` beside the envelope fields (#550). An unmarked
  // object or null used to be combined as an unknown input here, while the
  // Python twin raised; an input with no envelope is kept out at the source.
  // Checked before fn runs.
  for (let i = 0; i < items.length; i++) {
    if (!isMarkedValue(items[i]))
      throw new TypeError(`derive: input ${i} is not a marked value (mark it first)`);
  }
  const value = fn(...items.map(unwrap));
  const combined = combineProvenance(...items.map(metaOf));
  const safeOverride = {};
  // An undefined override is no override, for every key (#533): the law's
  // result stands. For source, makeMeta's leaf rule (#177, source is
  // required) is not for derive; for confidence it reset the combined rung to
  // "none", and for confidenceScore it dropped the combined score, so a
  // caller passing an unset option silently lost what the law computed.
  // Each value is read once, so a getter cannot pass the check with one
  // value and be copied with another (#533 review). A null is no override
  // too, for the optional keys (#566): it is JSON's "unset" and Python's
  // None, and it dropped the combined score. A null source or confidence is
  // still passed on, so makeMeta refuses it (#443).
  for (const key of OVERRIDE_KEYS) {
    if (!(key in metaOverride)) continue;
    const v = metaOverride[key];
    if (v === undefined || (v === null && OPTIONAL_OVERRIDE_KEYS.includes(key))) continue;
    safeOverride[key] = v;
  }
  // Route the override through makeMeta so derive is never weaker than the
  // constructor: an out-of-range confidenceScore (or unrankable weakestSource)
  // is dropped by the same validation, not stored raw. derivedFromMock is
  // force-OR'd *before* the call, so taint still cannot be cleared (the one law).
  // A malformed taint override is passed to makeMeta as it is, so makeMeta
  // refuses it with its own message and quoting (#555): read as taint it was
  // called mock, and it must not be dropped silently.
  const flag = metaOverride.derivedFromMock;
  const readable = flag === undefined || flag === null || typeof flag === "boolean";
  const merged = makeMeta({
    ...combined,
    ...safeOverride,
    derivedFromMock: readable ? combined.derivedFromMock || flag === true : flag,
  });
  return Object.freeze({ value, ...merged });
}
