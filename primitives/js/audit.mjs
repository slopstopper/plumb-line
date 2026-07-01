// audit.mjs — runtime consistency checker for provenance metadata.
import {
  CONFIDENCE,
  STATUS,
  weakestConfidence,
  weakestSource,
  isScore,
} from "./provenance.mjs";

const CLEAN_SOURCES = ["real", "semiReal", "fallback"];

/**
 * Checks a provenance metadata envelope for internal consistency.
 * Returns an empty array when the envelope is consistent; otherwise returns
 * one string per issue found. Issue prefixes:
 * - `"laundering:"` — a clean source combined with mock taint
 * - `"over-claiming:"` — confidence or confidenceScore higher than lineage supports
 * - `"source over-claim:"` — weakestSource cleaner than lineage proves
 * - `"taint dropped:"` — a tainted lineage step but derivedFromMock is false
 * - `"unreproducible:"` — source is "derived" but lineage is empty
 * - `"missing meta"` — input is not a plain object (null, undefined, or a non-object)
 * @param {object|null|undefined} meta - Envelope to audit
 * @returns {string[]} List of issue descriptions; empty means consistent
 */
export function auditMeta(meta) {
  if (!meta || typeof meta !== "object" || Array.isArray(meta)) return ["missing meta"];
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

// The four required fields (SPEC §1) and their type predicates, in the order
// they appear in the envelope table.
const REQUIRED_FIELDS = [
  ["source", (v) => typeof v === "string", "a string"],
  ["confidence", (v) => typeof v === "string", "a string"],
  ["derivedFromMock", (v) => typeof v === "boolean", "a boolean"],
  ["lineage", (v) => Array.isArray(v), "an array"],
];

// validateEnvelope — the *structural* checker, complementary to auditMeta.
// auditMeta verifies logical consistency among the fields that ARE present and
// tolerates absence as "unknown" (SPEC §2); it therefore passes a structurally
// empty `{}`. validateEnvelope verifies the four required fields (SPEC §1) are
// present and well-typed. Like auditMeta it is total: it returns a list of issue
// strings (empty = structurally valid) and never throws.
export function validateEnvelope(meta) {
  if (meta === null || meta === undefined) return ["missing meta"];
  if (typeof meta !== "object" || Array.isArray(meta)) {
    return ["not an envelope object"];
  }
  const issues = [];
  for (const [name, ok, typeLabel] of REQUIRED_FIELDS) {
    if (!(name in meta)) {
      issues.push(`missing required field: ${name}`);
    } else if (!ok(meta[name])) {
      issues.push(`field '${name}' must be ${typeLabel}`);
    }
  }
  return issues;
}
