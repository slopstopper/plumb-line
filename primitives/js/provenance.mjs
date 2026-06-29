// provenance.mjs — the provenance/lineage law (single source).

// Schema version of the provenance metadata envelope (Principle 7). Declared so
// consumers can pin to a shape; embedding it per-meta and validating against it
// is planned.
export const PROVENANCE_VERSION = 1;

export const STATUS = [
  "unavailable",
  "mock",
  "fallback",
  "semiReal",
  "derived",
  "real",
];
export const CONFIDENCE = ["none", "low", "medium", "high"];

export function isScore(x) {
  return typeof x === "number" && Number.isFinite(x) && x >= 0 && x <= 1;
}

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
    source,
    confidence,
    derivedFromMock:
      derivedFromMock === undefined
        ? source === "mock"
        : Boolean(derivedFromMock),
    lineage: Array.isArray(lineage) ? [...lineage] : [],
  };
  // Optional numeric confidence — a finer-grained companion to the ordinal
  // `confidence`, never a replacement. Stored only when it is a valid score.
  if (isScore(confidenceScore)) meta.confidenceScore = confidenceScore;
  // Computed-only resolution beyond the derivedFromMock boolean; passed through
  // here so chained derives carry it, but never settable as a derive override.
  if (STATUS.includes(weakestSource)) meta.weakestSource = weakestSource;
  if (basis !== undefined) meta.basis = basis;
  if (adapter !== undefined) meta.adapter = adapter;
  return meta;
}

export function weakestConfidence(...levels) {
  if (levels.length === 0) return "none";
  let minIdx = CONFIDENCE.length - 1;
  for (const level of levels) {
    const idx = CONFIDENCE.indexOf(level);
    minIdx = Math.min(minIdx, idx === -1 ? 0 : idx);
  }
  return CONFIDENCE[minIdx];
}

export function taints(meta) {
  return Boolean(meta?.derivedFromMock) || meta?.source === "mock";
}

// Least-trustworthy source among the given values, ranked by STATUS. Unknown
// values are ignored; returns undefined when nothing is rankable.
export function weakestSource(...sources) {
  let minIdx = STATUS.length;
  for (const s of sources) {
    const idx = STATUS.indexOf(s);
    if (idx !== -1) minIdx = Math.min(minIdx, idx);
  }
  return minIdx === STATUS.length ? undefined : STATUS[minIdx];
}

// Conservative numeric floor: the minimum, but only when every input carries a
// score. A missing score is "unknown" and cannot be dropped from a min, so any
// gap yields undefined (omit) rather than an over-claim.
export function combineConfidenceScore(scores) {
  if (scores.length === 0 || !scores.every(isScore)) return undefined;
  return Math.min(...scores);
}

let __stepCounter = 0;
export function __resetStepCounter() {
  __stepCounter = 0;
}
function nextStepId() {
  __stepCounter += 1;
  return `step-${__stepCounter}`;
}

export function combineProvenance(...metas) {
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
      id: nextStepId(),
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
  const lineage = [...priorLineage, ...inputSteps];
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
