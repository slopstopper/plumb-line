// marked.mjs — thin wrapper sugar over the provenance law. The law lives in provenance.mjs.
import { combineProvenance, makeMeta } from "./provenance.mjs";

const META_KEYS = [
  "source",
  "confidence",
  "derivedFromMock",
  "lineage",
  "basis",
  "adapter",
];

export function mark(value, metaInput = {}) {
  return { value, ...makeMeta(metaInput) };
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
  const merged = {
    ...combined,
    ...metaOverride,
    derivedFromMock:
      combined.derivedFromMock || Boolean(metaOverride.derivedFromMock),
  };
  return { value, ...merged };
}
