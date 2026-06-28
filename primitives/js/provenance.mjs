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
