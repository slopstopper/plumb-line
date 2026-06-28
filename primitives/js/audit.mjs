// audit.mjs — runtime consistency checker for provenance metadata.
import { CONFIDENCE, weakestConfidence } from "./provenance.mjs";

const CLEAN_SOURCES = ["real", "semiReal", "fallback"];

export function auditMeta(meta) {
  if (!meta) return ["missing meta"];
  const issues = [];
  const lineage = Array.isArray(meta.lineage) ? meta.lineage : [];

  if (CLEAN_SOURCES.includes(meta.source) && meta.derivedFromMock === true) {
    issues.push(
      `laundering: clean source '${meta.source}' but derivedFromMock is true`,
    );
  }

  const lineageConfidences = lineage
    .map((s) => s?.confidence)
    .filter((c) => CONFIDENCE.includes(c));
  if (lineageConfidences.length > 0) {
    const weakest = weakestConfidence(...lineageConfidences);
    if (CONFIDENCE.indexOf(meta.confidence) > CONFIDENCE.indexOf(weakest)) {
      issues.push(
        `over-claiming: confidence '${meta.confidence}' exceeds weakest lineage confidence '${weakest}'`,
      );
    }
  }

  const lineageTainted = lineage.some(
    (s) => Boolean(s?.derivedFromMock) || s?.source === "mock",
  );
  if (lineageTainted && meta.derivedFromMock === false) {
    issues.push(
      "taint dropped: lineage contains a tainted step but derivedFromMock is false",
    );
  }

  if (meta.source === "derived" && lineage.length === 0) {
    issues.push("unreproducible: derived value has no lineage");
  }

  return issues;
}
