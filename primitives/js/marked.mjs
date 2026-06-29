// marked.mjs — thin wrapper sugar over the provenance law. The law lives in provenance.mjs.
import { combineProvenance, makeMeta } from "./provenance.mjs";

const META_KEYS = [
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

export function mark(value, metaInput = {}) {
  return Object.freeze({ value, ...makeMeta(metaInput) });
}

export function unwrap(marked) {
  return marked?.value;
}

export function metaOf(marked) {
  const meta = {};
  for (const key of META_KEYS)
    if (key in (marked || {})) meta[key] = marked[key];
  return meta;
}

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
