// audit.mjs — runtime consistency checker for provenance metadata.
import {
  CONFIDENCE,
  STATUS,
  weakestConfidence,
  weakestSource,
  isScore,
} from "./provenance.mjs";

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

  // An unknown confidence on a step is laundering, not "no signal": treat it as
  // the `none` floor (mirroring weakestConfidence), so audit is never laxer than
  // the combination law. A step that records *no* confidence is still skipped —
  // absence is genuinely unrankable and must not manufacture a false over-claim.
  const lineageConfidences = lineage
    .map((s) => s?.confidence)
    .filter((c) => c != null)
    .map((c) => (CONFIDENCE.includes(c) ? c : "none"));
  if (lineageConfidences.length > 0) {
    const weakest = weakestConfidence(...lineageConfidences);
    if (CONFIDENCE.indexOf(meta.confidence) > CONFIDENCE.indexOf(weakest)) {
      issues.push(
        `over-claiming: confidence '${meta.confidence}' exceeds weakest lineage confidence '${weakest}'`,
      );
    }
  }

  // Numeric over-claiming — the higher-resolution analog of the ordinal check.
  if (isScore(meta.confidenceScore)) {
    const lineageScores = lineage
      .map((s) => s?.confidenceScore)
      .filter((c) => isScore(c));
    if (lineageScores.length > 0) {
      const weakest = Math.min(...lineageScores);
      if (meta.confidenceScore > weakest) {
        issues.push(
          `over-claiming: confidenceScore ${meta.confidenceScore} exceeds weakest lineage score ${weakest}`,
        );
      }
    }
  }

  // Source over-claim — weakestSource cannot look cleaner than the lineage proves.
  if (STATUS.includes(meta.weakestSource)) {
    const actual = weakestSource(...lineage.map((s) => s?.source));
    if (actual && STATUS.indexOf(meta.weakestSource) > STATUS.indexOf(actual)) {
      issues.push(
        `source over-claim: weakestSource '${meta.weakestSource}' is cleaner than lineage's '${actual}'`,
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
