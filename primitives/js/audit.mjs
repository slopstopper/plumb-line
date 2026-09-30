// audit.mjs — runtime consistency checker for provenance metadata.
import {
  CONFIDENCE,
  STATUS,
  weakestConfidence,
  weakestSource,
  isScore,
  PROVENANCE_VERSION,
  taints,
} from "./provenance.mjs";

const CLEAN_SOURCES = ["real", "semiReal", "fallback"];

/** The weakest of a stated weakestSource and every lineage step whose
 * source is on the ladder; undefined when none is known. Steps with an unknown
 * source are skipped: the weakest known source is an upper bound on the true
 * floor, so a source cleaner than it is an over-claim whatever the unknown
 * steps hold (#551 verification). A loop, not a spread, so a long lineage
 * cannot overflow the stack here. Python twin: _ancestry_floor. */
function ancestryFloor(stated, lineage) {
  let floor = STATUS.includes(stated) ? STATUS.indexOf(stated) : -1;
  for (const s of lineage) {
    if (!STATUS.includes(s?.source)) continue;
    const i = STATUS.indexOf(s.source);
    if (floor === -1 || i < floor) floor = i;
  }
  return floor === -1 ? undefined : STATUS[floor];
}

/**
 * Checks a provenance metadata envelope for internal consistency.
 * Returns an empty array when the envelope is consistent; otherwise returns
 * one string per issue found. Issue prefixes:
 * - `"laundering:"` — a clean source combined with mock taint
 * - `"over-claiming:"` — confidence or confidenceScore higher than lineage supports
 * - `"source over-claim:"` — weakestSource cleaner than lineage proves, or
 *   stated over a lineage with an unknown source; a source (other than
 *   "derived") cleaner than its ancestry's weakest source (#556); with no
 *   lineage, weakestSource cleaner than source (#553)
 * - `"unknown source:"` — a lineage step that is not an object, or whose
 *   source is missing, null or off the ladder (#551)
 * - `"malformed taint flag:"` — a lineage step whose derivedFromMock is not a
 *   boolean; null counts as absent (#551, #555)
 * - `"taint dropped:"` — a tainted lineage step but derivedFromMock is false
 * - `"unreproducible:"` — source is "derived" but lineage is empty
 * - `"missing meta"` — null, undefined, a primitive, an array, or any object
 *   outside the non-plain set (Map/Date/class instance)
 * - `"non-plain meta:"` — the wrong container type for an envelope (#209): a
 *   null-prototype object (pollution-safe JSON parsers); rebuild with {...meta}
 * - `"version-legacy:"` — envelope predates the current provenance version, or omits it
 * - `"version-future:"` — envelope reports a newer version than this checker supports
 * - `"version-malformed:"` — the version field is present but is not a finite
 *   number (#156), or is finite with a fractional part (#216) — SPEC §5b
 *   carries an integer, judged on the value (2.0 is valid; 1.5 is not).
 * @param {object|null|undefined} meta - Envelope to audit
 * @returns {string[]} List of issue descriptions; empty means consistent
 */
export function auditMeta(meta) {
  if (meta === null || typeof meta !== "object") return ["missing meta"];
  if (Object.getPrototypeOf(meta) !== Object.prototype) {
    // "Wrong container type" is a different fact from "no envelope" (#209):
    // a null-prototype object is what pollution-safe JSON parsers hand back,
    // and calling one that carries an envelope "missing" hides every real
    // finding behind a wrong diagnostic. The split is judged on container
    // type alone, scoped to what each language's JSON ecosystem actually
    // produces around the plain type (Python: dict subclasses via
    // object_pairs_hook). A Map/Date/class instance stays "missing meta" in
    // both languages because no JSON parser yields one — not because it
    // could not hold the fields.
    if (!Array.isArray(meta) && Object.getPrototypeOf(meta) === null)
      return ["non-plain meta: envelope is not a plain dict/object; rebuild it with dict(meta) / {...meta}"];
    return ["missing meta"];
  }
  const issues = [];

  // Version read policy (#93): forgiving forward, honest backward. Advisory only.
  // Absent is legacy (an envelope predating the field). Present-but-not-a-number
  // is malformed, NOT legacy (#156) — saying "predates version N" about a list or
  // a bool asserts something false. Booleans are excluded explicitly: `typeof
  // true === "boolean"` in JS, but Python's bool is an int subclass, so the two
  // checkers only agree here if both rule it out on purpose.
  const v = meta.provenanceVersion;
  if (v === undefined) {
    issues.push(`version-legacy: envelope predates version ${PROVENANCE_VERSION}`);
  } else if (typeof v !== "number" || !Number.isFinite(v)) {
    issues.push(`version-malformed: provenance version is not a finite number`);
  } else if (!Number.isInteger(v)) {
    // SPEC §5b: the field carries an integer. A fractional version is at
    // least numerically comparable to the current one, but "predates
    // version 2" said of 1.5 asserts contract-conformance it lacks (#216).
    // Integrality of the VALUE, not the type: JSON has no int/float
    // distinction, so 2.0 must stay valid in both languages.
    issues.push(`version-malformed: provenance version is not an integer`);
  } else if (v < PROVENANCE_VERSION) {
    issues.push(`version-legacy: envelope predates version ${PROVENANCE_VERSION}`);
  } else if (v > PROVENANCE_VERSION) {
    issues.push(`version-future: envelope version ${v} is newer than supported ${PROVENANCE_VERSION}`);
  }

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
    // Folded pairwise, not spread: a spread passes one argument per step, and
    // a long lineage overflowed the stack (#560). The same below.
    const weakest = lineageConfidences.reduce((a, b) => weakestConfidence(a, b));
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
      const weakest = lineageScores.reduce((a, b) => Math.min(a, b));
      if (meta.confidenceScore > weakest) {
        issues.push(
          `over-claiming: confidenceScore ${meta.confidenceScore} exceeds weakest lineage score ${weakest}`,
        );
      }
    }
  }

  // Source over-claim — weakestSource cannot look cleaner than the lineage proves.
  if (STATUS.includes(meta.weakestSource)) {
    const actual = lineage.reduce((weakest, s) => weakestSource(weakest, s?.source), undefined);
    if (actual && STATUS.indexOf(meta.weakestSource) > STATUS.indexOf(actual)) {
      issues.push(
        `source over-claim: weakestSource '${meta.weakestSource}' is cleaner than lineage's '${actual}'`,
      );
    }
  }

  // Only a boolean true taints (SPEC §3, #555): Boolean() read [] as tainted
  // here and not in the Python twin. A malformed step flag is not taint.
  const lineageTainted = lineage.some((s) => taints(s));
  if (lineageTainted && meta.derivedFromMock === false) {
    issues.push(
      "taint dropped: lineage contains a tainted step but derivedFromMock is false",
    );
  }

  if (meta.source === "derived" && lineage.length === 0) {
    issues.push("unreproducible: derived value has no lineage");
  }

  // A value relabelled above its own ancestry (#556): a source cleaner than
  // the weakest source its ancestry shows, from the stated weakestSource and,
  // when every step's source is known, the lineage itself (a handed envelope
  // can omit weakestSource). "derived" is the law's own label for a computed
  // value, not a claim about its inputs, so it is exempt as the source. A
  // floor of "derived" is exempt only when the lineage also shows a real
  // step, as a derive of a derive of real data has (#556 review): a lineage
  // of derived steps alone, or a leaf that states it, shows no real data at
  // all, for example a value re-marked "derived" with its lineage dropped
  // (#551 verification).
  const floor = ancestryFloor(meta.weakestSource, lineage);
  const realShown = lineage.some((s) => s?.source === "real");
  if (meta.source !== "derived" && STATUS.includes(meta.source) && floor !== undefined
      && !(floor === "derived" && realShown)
      && STATUS.indexOf(meta.source) > STATUS.indexOf(floor)) {
    issues.push(`source over-claim: source '${meta.source}' is cleaner than its ancestry's weakest source '${floor}'`);
  }
  // A stated weakestSource over a lineage with an unknown source cannot be
  // shown: the law omits it there (§3 rule 6), and check 4 reads the known
  // steps alone (#551 review).
  if (STATUS.includes(meta.weakestSource) && lineage.some((s) => !STATUS.includes(s?.source))) {
    issues.push(`source over-claim: weakestSource '${meta.weakestSource}' cannot be shown: a lineage step's source is unknown`);
  }
  // A leaf's weakestSource cleaner than its own source, with no lineage to
  // show it (#553): check 4 above has nothing to compare it with.
  if (lineage.length === 0 && STATUS.includes(meta.source) && STATUS.includes(meta.weakestSource)
      && STATUS.indexOf(meta.weakestSource) > STATUS.indexOf(meta.source)) {
    issues.push(`source over-claim: weakestSource '${meta.weakestSource}' is cleaner than source '${meta.source}', with no lineage to show it`);
  }

  // Name what cannot be read, rather than reading it as clean (#551): a step
  // whose source is unknown, and a step whose taint flag is not a boolean
  // (#555 made that neither taint nor clean). The value is not quoted, so the
  // message is the same in both twins.
  lineage.forEach((s, i) => {
    if (s === null || typeof s !== "object" || Array.isArray(s)) {
      issues.push(`unknown source: lineage step ${i} is not an object`);
      return;
    }
    if (s.source === undefined || s.source === null) {
      issues.push(`unknown source: lineage step ${i} has no source`);
    } else if (!STATUS.includes(s.source)) {
      issues.push(`unknown source: lineage step ${i} source is not on the source ladder`);
    }
    if (s.derivedFromMock !== undefined && s.derivedFromMock !== null && typeof s.derivedFromMock !== "boolean") {
      issues.push(`malformed taint flag: lineage step ${i} derivedFromMock is not a boolean`);
    }
  });

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
// empty `{}` except for the version-legacy advisory (#93), since `{}` omits
// provenanceVersion. validateEnvelope verifies the four required fields (SPEC §1) are
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
