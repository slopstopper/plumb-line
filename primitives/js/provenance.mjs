// provenance.mjs — the provenance/lineage law (single source).
export const STATUS = [
  "unavailable",
  "mock",
  "fallback",
  "semiReal",
  "derived",
  "real",
];
export const CONFIDENCE = ["none", "low", "medium", "high"];

export function makeMeta({
  source = "derived",
  confidence = "none",
  derivedFromMock,
  lineage = [],
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
    lineage: Array.isArray(lineage) ? lineage : [],
  };
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
  const priorLineage = metas.flatMap((m) =>
    Array.isArray(m?.lineage) ? m.lineage : [],
  );
  const inputSteps = metas.map((m) => ({
    id: nextStepId(),
    of: "input",
    source: m?.source,
    confidence: m?.confidence,
    derivedFromMock: taints(m),
  }));
  return makeMeta({
    source: "derived",
    confidence,
    derivedFromMock,
    lineage: [...priorLineage, ...inputSteps],
  });
}
