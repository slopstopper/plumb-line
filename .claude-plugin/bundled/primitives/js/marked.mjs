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

/**
 * Wraps a value with provenance metadata, producing a marked value object.
 * The returned object is frozen; its `value` property holds the original value
 * and the remaining properties are the metadata envelope fields.
 * @param {*} value - Any value to track
 * @param {object} [metaInput={}] - Initial metadata; same options as {@link makeMeta}
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
  const value = fn(...inputs.map(unwrap));
  const combined = combineProvenance(...inputs.map(metaOf));
  const safeOverride = {};
  for (const key of OVERRIDE_KEYS) {
    if (key in metaOverride) safeOverride[key] = metaOverride[key];
  }
  // Route the override through makeMeta so derive is never weaker than the
  // constructor: an out-of-range confidenceScore (or unrankable weakestSource)
  // is dropped by the same validation, not stored raw. derivedFromMock is
  // force-OR'd *before* the call, so taint still cannot be cleared (the one law).
  const merged = makeMeta({
    ...combined,
    ...safeOverride,
    derivedFromMock:
      combined.derivedFromMock || Boolean(metaOverride.derivedFromMock),
  });
  return Object.freeze({ value, ...merged });
}
