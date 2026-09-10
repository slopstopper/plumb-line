// primitives/js/baseline.mjs — Principle 9: golden baseline + explain-the-drift.
//
// Pins a marked value WITH its trust state, diffs later runs against the pin,
// refuses silent drift, and requires a recorded explanation to accept a new
// state. Attribution is what separates this from snapshot testing: the
// envelope's lineage records each input's state at combination time, so a
// drift can say which input moved. See docs/adr/0015-baseline-library-first.md
// and SPEC §4 for the lineage shape. Mirror of primitives/python/baseline.py;
// parity is pinned by primitives/conformance/baseline-cases.json.
import { PROVENANCE_VERSION } from "./provenance.mjs";

export const BASELINE_FORMAT = "v1";
export const NAME_RE = /^[A-Za-z0-9._-]+$/;
export const STEP_FIELDS = ["source", "confidence", "confidenceScore", "derivedFromMock", "of"];
export const TOP_FIELDS = ["source", "confidence", "confidenceScore", "derivedFromMock"];

// ---------- canonical JSON ----------

export function canonicalize(x) {
  if (Array.isArray(x)) return x.map(canonicalize);
  if (x && typeof x === "object") {
    const out = {};
    for (const k of Object.keys(x).sort()) out[k] = canonicalize(x[k]);
    return out;
  }
  return x;
}

export function canonicalJson(x) {
  return JSON.stringify(canonicalize(x), null, 2) + "\n";
}

export function compactJson(x) {
  const s = JSON.stringify(canonicalize(x));
  return s === undefined ? "null" : s;
}

export function isJsonValue(x) {
  try {
    const s = JSON.stringify(x);
    if (s === undefined) return false;
    return deepEqual(JSON.parse(s), x);
  } catch {
    return false;
  }
}

export function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    return deepEqual(ka, kb) && ka.every((k) => deepEqual(a[k], b[k]));
  }
  return false;
}

// ---------- attribution ----------

function finding(path, before, after, text) {
  return { path, before: before === undefined ? null : before, after: after === undefined ? null : after, text };
}

const fieldText = (path, b, a) => `${path}: ${compactJson(b)} -> ${compactJson(a)}`;

/**
 * Compare a pinned record against a new wire-form envelope + value.
 * Returns findings in the fixed order: version, per-step fields, lineage
 * length, top-level fields not explained by a step finding, value.
 */
export function compare(record, wireMeta, value, runningVersion = PROVENANCE_VERSION) {
  const f = [];
  if (record.provenanceVersion !== runningVersion) {
    f.push(finding("provenanceVersion", record.provenanceVersion, runningVersion,
                   `pinned under wire v${record.provenanceVersion}, running v${runningVersion}`));
  }
  const pl = Array.isArray(record.meta?.lineage) ? record.meta.lineage : [];
  const nl = Array.isArray(wireMeta?.lineage) ? wireMeta.lineage : [];
  const touched = new Set();
  for (let i = 0; i < Math.min(pl.length, nl.length); i++) {
    for (const field of STEP_FIELDS) {
      const b = pl[i]?.[field], a = nl[i]?.[field];
      if (!deepEqual(b === undefined ? null : b, a === undefined ? null : a)) {
        const path = `meta.lineage[${i}].${field}`;
        f.push(finding(path, b, a, fieldText(path, b, a)));
        touched.add(field);
      }
    }
  }
  if (pl.length !== nl.length) {
    const grew = nl.length > pl.length;
    const n = Math.abs(nl.length - pl.length);
    const k = Math.min(pl.length, nl.length);
    f.push(finding("meta.lineage.length", pl.length, nl.length,
                   grew ? `lineage grew by ${n} (first new step: meta.lineage[${k}])`
                        : `lineage shrank by ${n} (first missing step: meta.lineage[${k}])`));
    touched.add("length");
  }
  for (const field of TOP_FIELDS) {
    const b = record.meta?.[field], a = wireMeta?.[field];
    if (!touched.has(field) && !deepEqual(b === undefined ? null : b, a === undefined ? null : a)) {
      const path = `meta.${field}`;
      f.push(finding(path, b, a, fieldText(path, b, a)));
    }
  }
  if (!deepEqual(record.value, value)) {
    const attributed = f.some((x) => x.path.startsWith("meta."));
    f.push(finding("value", record.value, value,
                   attributed ? "value moved; attributed to the findings above"
                              : "value moved with no input change"));
  }
  return f;
}

export function summarize(findings) {
  return findings.length ? findings.map((x) => x.text).join("; ") : "none";
}
