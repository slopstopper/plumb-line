// provenance.mjs — the provenance/lineage law (single source).

import { createHash } from "node:crypto";

// Schema version of the provenance metadata envelope (Principle 7). Declared so
// consumers can pin to a shape; every envelope now carries this constant
// (embedded by makeMeta); validating envelopes against it is planned.
export const PROVENANCE_VERSION = 2;

export const STATUS = [
  "unavailable",
  "mock",
  "inferred",
  "fallback",
  "semiReal",
  "derived",
  "real",
];
export const CONFIDENCE = ["none", "low", "medium", "high"];

/**
 * Returns true when x is a finite number in [0, 1].
 * @param {*} x
 * @returns {boolean}
 */
export function isScore(x) {
  return typeof x === "number" && Number.isFinite(x) && x >= 0 && x <= 1;
}

/**
 * Constructs a frozen provenance metadata envelope.
 * @param {object} [opts]
 * @param {string} [opts.source="derived"] - One of {@link STATUS}
 * @param {string} [opts.confidence="none"] - One of {@link CONFIDENCE}
 * @param {number} [opts.confidenceScore] - Numeric precision in [0, 1]; omitted when invalid
 * @param {boolean} [opts.derivedFromMock] - Defaults to `source === "mock"`
 * @param {object[]} [opts.lineage=[]] - Prior lineage steps; each step is frozen
 * @param {string} [opts.weakestSource] - Lowest-ranked source in ancestry; one of {@link STATUS}
 * @param {*} [opts.basis] - Arbitrary domain metadata (passed through unchanged)
 * @param {*} [opts.adapter] - Adapter identifier (passed through unchanged)
 * @returns {Readonly<object>} Frozen envelope
 */
export function makeMeta({
  source = "derived",
  confidence = "none",
  confidenceScore,
  derivedFromMock,
  lineage = [],
  weakestSource,
  basis,
  adapter,
} = {}) {
  const meta = {
    provenanceVersion: PROVENANCE_VERSION,
    source,
    confidence,
    derivedFromMock:
      derivedFromMock === undefined
        ? source === "mock"
        : Boolean(derivedFromMock),
    // Each meta owns a *frozen copy* of its lineage. Steps are cloned then
    // frozen so (a) an envelope's recorded history can't be rewritten in place,
    // and (b) a step shared across parent/child metas can't leak a mutation from
    // one into the other — the audit trail an auditMeta() trusts stays intact.
    lineage: Object.freeze(
      (Array.isArray(lineage) ? lineage : []).map((s) =>
        s && typeof s === "object" ? Object.freeze({ ...s }) : s,
      ),
    ),
  };
  // Optional numeric confidence — a finer-grained companion to the ordinal
  // `confidence`, never a replacement. Stored only when it is a valid score.
  if (isScore(confidenceScore)) meta.confidenceScore = confidenceScore;
  // Computed-only resolution beyond the derivedFromMock boolean; passed through
  // here so chained derives carry it, but never settable as a derive override.
  if (STATUS.includes(weakestSource)) meta.weakestSource = weakestSource;
  if (basis !== undefined) meta.basis = basis;
  if (adapter !== undefined) meta.adapter = adapter;
  return Object.freeze(meta);
}

/**
 * Returns the weakest (lowest-ranked) confidence level among the given values.
 * Unknown values are treated as `"none"`. Returns `"none"` when called with no arguments.
 * @param {...string} levels - Values from {@link CONFIDENCE}
 * @returns {string} Weakest confidence level
 */
export function weakestConfidence(...levels) {
  if (levels.length === 0) return "none";
  let minIdx = CONFIDENCE.length - 1;
  for (const level of levels) {
    const idx = CONFIDENCE.indexOf(level);
    minIdx = Math.min(minIdx, idx === -1 ? 0 : idx);
  }
  return CONFIDENCE[minIdx];
}

/**
 * Returns true when the envelope carries mock taint
 * (either `derivedFromMock` is truthy or `source` is `"mock"`).
 * @param {object|null|undefined} meta
 * @returns {boolean}
 */
export function taints(meta) {
  return Boolean(meta?.derivedFromMock) || meta?.source === "mock";
}

/**
 * Returns the least-trustworthy source among the given values, ranked by {@link STATUS}.
 * Unknown values are ignored. Returns `undefined` when nothing is rankable.
 * @param {...string} sources - Values from {@link STATUS}
 * @returns {string|undefined}
 */
export function weakestSource(...sources) {
  let minIdx = STATUS.length;
  for (const s of sources) {
    const idx = STATUS.indexOf(s);
    if (idx !== -1) minIdx = Math.min(minIdx, idx);
  }
  return minIdx === STATUS.length ? undefined : STATUS[minIdx];
}

/**
 * Returns the minimum of an array of numeric confidence scores,
 * but only when every element is a valid score. Returns `undefined` if any
 * element is missing or invalid — a gap is "unknown", not zero.
 * @param {number[]} scores
 * @returns {number|undefined}
 */
export function combineConfidenceScore(scores) {
  if (scores.length === 0 || !scores.every(isScore)) return undefined;
  return Math.min(...scores);
}

// Deprecated no-op, kept for import compatibility. Step IDs are now assigned by
// a counter local to each combineProvenance call (see below), so there is no
// shared state to reset between runs. Safe to delete from call sites.
export function __resetStepCounter() {}

/**
 * Applies the taint-propagation combination law to one or more metadata envelopes
 * and returns a new derived envelope. This is the core invariant: mock taint
 * propagates forward and cannot be cleared.
 *
 * Calling with zero arguments returns an `"unavailable"` envelope (not `"derived"`),
 * because a value derived from nothing has no honest provenance.
 *
 * @param {...object} metas - Provenance envelopes produced by {@link makeMeta}
 * @returns {Readonly<object>} Combined envelope with `source: "derived"`
 */
export function combineProvenance(...metas) {
  // A value combined from no inputs is derived from nothing — honestly
  // 'unavailable', not 'derived'. Returning 'derived' with an empty lineage
  // would contradict auditMeta's "derived value has no lineage" check
  // (SPEC §3 vs §5). See #25.
  if (metas.length === 0) {
    return makeMeta({
      source: "unavailable",
      confidence: "none",
      derivedFromMock: false,
      lineage: [],
    });
  }
  const derivedFromMock = metas.some((m) => taints(m));
  const confidence = weakestConfidence(...metas.map((m) => m?.confidence));
  const confidenceScore = combineConfidenceScore(
    metas.map((m) => m?.confidenceScore),
  );
  const priorLineage = metas.flatMap((m) =>
    Array.isArray(m?.lineage) ? m.lineage : [],
  );
  const inputSteps = metas.map((m) => {
    const step = {
      of: "input",
      source: m?.source,
      confidence: m?.confidence,
      derivedFromMock: taints(m),
    };
    // Record the numeric score too when the input carries one, so the numeric
    // over-claim audit works on real derive output, not just hand-built metas.
    if (isScore(m?.confidenceScore)) step.confidenceScore = m.confidenceScore;
    return step;
  });
  // Renumber the *entire* output lineage from a combine-local counter, so step
  // IDs are unique-within-output (SPEC §4) for every input shape — two
  // independently-built inputs each start at step-1, so seeding past the prior
  // length alone wouldn't stop their inherited steps from colliding. No
  // module-level state means concurrent combines can't collide either. IDs are
  // thus a pure function of output structure, not creation order. See #23.
  const lineage = [...priorLineage, ...inputSteps].map((s, i) => ({
    ...s,
    id: `step-${i + 1}`,
  }));
  return makeMeta({
    source: "derived",
    confidence,
    confidenceScore,
    derivedFromMock,
    lineage,
    // Weakest source anywhere in the ancestry, read off the full lineage.
    weakestSource: weakestSource(...lineage.map((s) => s?.source)),
  });
}

/**
 * Content-addressed id for a lineage step (#52). Pure function of the step's
 * semantic fields plus the sorted ids of its input steps — so a step's id is
 * independent of what it is later combined with (stable across recombination).
 * @param {object} step
 * @param {string[]} inputIds
 * @returns {string} `"sha256:" + first 12 hex chars`
 */
export function stepId(step, inputIds = []) {
  const score = isScore(step?.confidenceScore) ? JSON.stringify(step.confidenceScore) : "-";
  const canon = [
    `of=${step?.of ?? ""}`,
    `source=${step?.source ?? ""}`,
    `confidence=${step?.confidence ?? ""}`,
    `derivedFromMock=${step?.derivedFromMock ? "true" : "false"}`,
    `confidenceScore=${score}`,
    `inputs=${[...inputIds].sort().join(",")}`,
  ].join("\n");
  return "sha256:" + createHash("sha256").update(canon).digest("hex").slice(0, 12);
}
