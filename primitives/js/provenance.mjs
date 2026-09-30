// provenance.mjs — the provenance/lineage law (single source).

import { createHash } from "node:crypto";

// Schema version of the provenance metadata envelope (Principle 7). Declared so
// consumers can pin to a shape; every envelope now carries this constant
// (embedded by makeMeta and validated on read).
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

/** A refused value as a message fragment. JSON where it can be; never
 * throws, so a BigInt or a cycle cannot replace the refusal with a
 * serialisation error, and NaN/Infinity read as themselves, not "null".
 * The Python twin (_json) agrees on the prefix of the message; the quoted
 * value can differ in form (floats, non-ASCII text, containers). */
function quote(value) {
  if (typeof value === "number" && !Number.isFinite(value)) return String(value);
  try {
    const s = JSON.stringify(value);
    return s === undefined ? String(value) : s;
  } catch {
    try {
      return String(value);
    } catch {
      try {
        // A null-prototype object has no toString either.
        return Object.prototype.toString.call(value);
      } catch {
        // A revoked Proxy, or one whose traps throw, cannot even be tagged.
        return "<unprintable>";
      }
    }
  }
}

// The step fields the law, the audit and the guard read.
const STEP_FIELDS = ["of", "source", "confidence", "derivedFromMock", "confidenceScore", "id"];

// How many objects fromObjectPrototype examines, the step included. Only an
// endless Proxy chain or an ordinary one over 10,000 deep reaches it; an
// ordinary chain cannot cycle.
const MAX_CHAIN = 10000;

// The methods every Object.prototype holds, in any realm.
const OBJECT_PROTOTYPE_METHODS = ["hasOwnProperty", "isPrototypeOf", "propertyIsEnumerable"];

/** Whether `o` is an Object.prototype, this realm's or another's (a `vm`
 * context, an iframe): the end of an ordinary prototype chain, and no step's
 * own. Another realm's is recognised by shape, as instanceof cannot: a null
 * prototype and the three methods as its own non-enumerable function-valued
 * data properties, as a real one holds them. An object built from data (JSON,
 * Object.assign) holds them enumerable, so it is not taken for one. */
function isObjectPrototype(o) {
  if (o === Object.prototype) return true;
  if (Object.getPrototypeOf(o) !== null) return false;
  return OBJECT_PROTOTYPE_METHODS.every((k) => {
    const d = Object.getOwnPropertyDescriptor(o, k);
    return d !== undefined && !d.enumerable && typeof d.value === "function";
  });
}

/** Whether `value`, read from step `s` as `s[k]`, comes from an
 * Object.prototype (a polluted global) rather than from the step: the chain
 * reaches an Object.prototype holding `k` before any object that defines it.
 * There it is decided by the descriptor, never by reading again: a data
 * field counts as pollution when it holds this value, and an accessor always
 * does, since a getter can answer differently each time. Baked into a frozen
 * copy, a polluted value would outlive the pollution, and a polluted source
 * would pass for a known one. The walk examines at most MAX_CHAIN objects and
 * stops at a cycle; if it cannot decide (the bound, a cycle, a throwing Proxy
 * trap), the value counts as the step's, as the law reads it. */
function fromObjectPrototype(s, k, value) {
  const seen = new Set();
  try {
    for (let o = s; o !== null && !seen.has(o) && seen.size < MAX_CHAIN; o = Object.getPrototypeOf(o)) {
      if (isObjectPrototype(o)) {
        const d = Object.getOwnPropertyDescriptor(o, k);
        return d !== undefined && (!("value" in d) || Object.is(d.value, value));
      }
      if (Object.hasOwn(o, k)) return false;
      seen.add(o);
    }
  } catch {
    // A Proxy trap that throws: undecided.
  }
  return false;
}

/** A frozen plain copy of an object lineage step (#548). Its own enumerable
 * fields are copied, as before; a copy of those only lost a law field the
 * step inherits, taint included, so one combine cleared it. So each law field
 * the copy lacks is read from the step as the law and the audit read it,
 * `s[k]`, whatever holds it (a prototype, a Proxy, a getter), and kept unless
 * it is undefined or comes from an Object.prototype. Only law fields are
 * read: an inherited method such as toJSON would change what the stored step
 * says. A read that throws propagates (SPEC §3). Python has no prototype
 * chain: a Mapping step is copied by its items. */
function copyStep(s) {
  const copy = { ...s };
  for (const k of STEP_FIELDS) {
    if (Object.hasOwn(copy, k)) continue;
    const value = s[k];
    if (value === undefined || fromObjectPrototype(s, k, value)) continue;
    Object.defineProperty(copy, k, { value, enumerable: true, writable: true, configurable: true });
  }
  return Object.freeze(copy);
}

/**
 * Constructs a frozen provenance metadata envelope.
 * @param {object} opts
 * @param {string} opts.source - One of {@link STATUS}; required, with no
 *   default (#177): a leaf has no parents, so it must say where it came from
 * @param {string} [opts.confidence="none"] - One of {@link CONFIDENCE}
 * @param {number} [opts.confidenceScore] - Numeric precision in [0, 1]; omitted when invalid
 * @param {boolean} [opts.derivedFromMock] - Defaults to `source === "mock"`
 * @param {object[]} [opts.lineage=[]] - Prior lineage steps; each step is frozen
 * @param {string} [opts.weakestSource] - Lowest-ranked source in ancestry; one of {@link STATUS}
 * @param {*} [opts.basis] - Arbitrary domain metadata (passed through unchanged)
 * @param {*} [opts.adapter] - Adapter identifier (passed through unchanged)
 * @returns {Readonly<object>} Frozen envelope
 * @throws {Error} When `source` is missing ("source is required", #177), or
 *   `source` is not in {@link STATUS} or `confidence` is not in
 *   {@link CONFIDENCE} (#443; the message starts "source must be one of" /
 *   "confidence must be one of"). An error thrown while a lineage step's
 *   fields are read (a getter, a Proxy trap) propagates (SPEC §3).
 */
export function makeMeta({
  source,
  confidence = "none",
  confidenceScore,
  derivedFromMock,
  lineage = [],
  weakestSource,
  basis,
  adapter,
} = {}) {
  // An out-of-vocabulary rung or source is refused here, not flagged later
  // (#443, owner decision 2026-09-28; ADR-0019): stored, it passed auditMeta
  // silently and the law quietly read it as the weakest rung (SPEC §2).
  // Python twin: make_meta; the message prefix is the same in both
  // (cases.json "construct"). A missing source has no default (#177, owner
  // decision 2026-09-28): the old "derived" was untrue of a leaf, which has no
  // parents, and audited as unreproducible.
  if (source === undefined)
    throw new Error(`source is required (one of ${STATUS.join(", ")})`);
  if (!STATUS.includes(source))
    throw new Error(`source must be one of ${STATUS.join(", ")}; got ${quote(source)}`);
  if (!CONFIDENCE.includes(confidence))
    throw new Error(`confidence must be one of ${CONFIDENCE.join(", ")}; got ${quote(confidence)}`);
  // A taint flag that is not a boolean is refused, as an off-ladder rung is
  // (#555, ADR-0019 amendment): read as taint it called an unreadable value
  // mock, and read by truthiness it disagreed with the Python twin. Absent or
  // null takes the default.
  if (!isTaintFlag(derivedFromMock))
    throw new Error(`derivedFromMock must be a boolean; got ${quote(derivedFromMock)}`);
  const meta = {
    provenanceVersion: PROVENANCE_VERSION,
    source,
    confidence,
    derivedFromMock: derivedFromMock ?? source === "mock",
    // Each meta owns a *frozen copy* of its lineage. Steps are cloned then
    // frozen so (a) an envelope's recorded history can't be rewritten in place,
    // and (b) a step shared across parent/child metas can't leak a mutation from
    // one into the other — the audit trail an auditMeta() trusts stays intact.
    lineage: Object.freeze(
      // An array step stays an array (#525): spread into an object it
      // became {"0": ..., "1": ...}, a history rewritten in the copy.
      (Array.isArray(lineage) ? lineage : []).map((s) =>
        Array.isArray(s) ? Object.freeze([...s])
          : s && typeof s === "object" ? copyStep(s) : s,
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
 * Whether a `derivedFromMock` value is one the law can read: a boolean, or
 * absent (`null` counts as absent). Anything else is malformed (#555): not
 * taint, since nothing shows it means mock, and not clean either. The
 * constructors refuse it and combine keeps it on its step as it is, so the
 * egress guard refuses it as invalid. Python twin: _is_taint_flag.
 * @param {unknown} value
 * @returns {boolean}
 */
function isTaintFlag(value) {
  return value === undefined || value === null || typeof value === "boolean";
}

/**
 * Returns true when the envelope carries mock taint: its `derivedFromMock` is
 * `true`, or its `source` is `"mock"` (SPEC §3). Only a boolean `true` taints:
 * a malformed flag is not read as mock (#555, reversing #525).
 * @param {object|null|undefined} meta
 * @returns {boolean}
 */
export function taints(meta) {
  return meta?.derivedFromMock === true || meta?.source === "mock";
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
  // -0 is returned as 0: Python's min() over 0.0 and -0.0 depends on argument
  // order, so the result would too (#525 review).
  const min = Math.min(...scores);
  return min === 0 ? 0 : min;
}

// Deprecated no-op, kept for import compatibility. Step IDs are now
// content-addressed (see stepId, #52) — there is no counter or other shared
// state to reset between runs. Safe to delete from call sites.
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
  // Prior steps keep their content-addressed ids verbatim — a subtree's id must
  // not change because it was recombined (#52). Only new input steps are minted.
  const priorLineage = metas.flatMap((m) =>
    Array.isArray(m?.lineage) ? m.lineage : [],
  );
  const inputSteps = metas.map((m) => {
    // The input's source and confidence, read as taint is read (through the
    // prototype), and null when it has none, as for an input that is not an
    // envelope (#525). A step always has both keys: the guard refuses a step
    // without them, and a key left off let a sourceless input through it.
    // A malformed taint flag is kept as the input carries it, neither read as
    // taint nor cleaned, so the guard refuses the step as invalid (#555).
    const step = {
      of: "input",
      source: m?.source ?? null,
      confidence: m?.confidence ?? null,
      derivedFromMock: isTaintFlag(m?.derivedFromMock) ? taints(m) : m.derivedFromMock,
    };
    // Record the numeric score too when the input carries one, so the numeric
    // over-claim audit works on real derive output, not just hand-built metas.
    if (isScore(m?.confidenceScore)) step.confidenceScore = m.confidenceScore;
    const priorIds = (Array.isArray(m?.lineage) ? m.lineage : [])
      .map((s) => s?.id)
      .filter((id) => typeof id === "string");
    step.id = stepId(step, priorIds);
    return step;
  });
  const lineage = [...priorLineage, ...inputSteps];
  return makeMeta({
    source: "derived",
    confidence,
    confidenceScore,
    derivedFromMock,
    lineage,
    // Weakest source anywhere in the ancestry, read off the full lineage, and
    // omitted when any step's source cannot be ranked (#551): read off the
    // known steps alone, an unknown ancestor left the result looking clean.
    weakestSource: lineage.every((s) => STATUS.includes(s?.source))
      ? weakestSource(...lineage.map((s) => s?.source))
      : undefined,
  });
}

/**
 * A number as its IEEE-754 binary64 bit pattern, 16 lowercase hex chars, with
 * -0 written as 0: JSON's -0 is -0 in JS and the integer 0 in Python (#525
 * review). Python twin: _double_hex.
 * @param {number} n
 * @returns {string}
 */
function doubleHex(n) {
  const buf = Buffer.alloc(8);
  buf.writeDoubleBE(n === 0 ? 0 : n);
  return buf.toString("hex");
}

/**
 * Compare two strings by Unicode code point, as Python's sorted() does. The
 * default sort compares UTF-16 code units, which puts a character above
 * U+FFFF before U+FFFF itself (#525 review).
 */
function byCodePoint(a, b) {
  const x = [...a];
  const y = [...b];
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (d !== 0) return d;
  }
  return x.length - y.length;
}

/**
 * One `of` / `source` / `confidence` value as the step-id canon writes it
 * (SPEC §4, #525). A string is itself and an absent value is empty, as
 * always; any other value a handed envelope can carry is written by type, the
 * same in both languages: a boolean as true/false, a number as its IEEE-754
 * bit pattern (so 1 and 1.0 agree), an array or object as <array> / <object>.
 * Python twin: _canon_field.
 * @param {unknown} v
 * @returns {string}
 */
function canonField(v) {
  if (v === undefined || v === null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number" || typeof v === "bigint") return doubleHex(Number(v));
  return Array.isArray(v) ? "<array>" : "<object>";
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
  // Canonical score encoding: IEEE-754 big-endian 8-byte representation as
  // lowercase hex. JSON.stringify/json.dumps disagree across languages for
  // small floats (e.g. 0.00001: JS "0.00001" vs Python "1e-05"), which would
  // otherwise produce different step ids for the same value cross-language.
  // The raw double bit pattern is identical in both, by construction.
  const score = isScore(step?.confidenceScore) ? doubleHex(step.confidenceScore) : "-";
  const canon = [
    `of=${canonField(step?.of)}`,
    `source=${canonField(step?.source)}`,
    `confidence=${canonField(step?.confidence)}`,
    // A boolean as true/false, absent as false, and a malformed flag (kept by
    // combine, #555) by type, as the fields above are.
    `derivedFromMock=${step?.derivedFromMock == null ? "false" : canonField(step.derivedFromMock)}`,
    `confidenceScore=${score}`,
    `inputs=${[...inputIds].sort(byCodePoint).join(",")}`,
  ].join("\n");
  return "sha256:" + createHash("sha256").update(canon).digest("hex").slice(0, 12);
}
