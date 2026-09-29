// vitest.mjs — the fixture quarantine for vitest (#123), on the
// `plumb-line-provenance/vitest` subpath. Tests are where fake data is
// supposed to live; this makes the quarantine explicit there. markFixture
// marks a fixture's value `source: "mock"`, so anything derived from it
// carries the taint; assertNoTaint and the toBeUntainted matcher fail a test
// when a golden output still carries it, and assertTainted (or
// `.not.toBeUntainted()`) checks that the taint did reach a value.
//
// Owner decisions on #123: marking is opt-in per fixture; the check takes a
// marked value only (#544). The check is the egress guard (#120, SPEC §5c)
// with its defaults. This module never imports vitest: register the matcher
// with `expect.extend(plumbMatchers)`. Python twin: pytest_plugin.py.
import { mark, metaOf } from "./marked.mjs";
import { guard, ProvenanceRefused } from "./guard.mjs";
import { validateEnvelope } from "./audit.mjs";

const NO_TAINT = "no mock taint may reach a golden output";
const TAINTED = "mock taint was expected to reach this value";

// A marked value, not data that happens to have a `value` key: a plain
// object whose own envelope fields form a structurally valid envelope
// (SPEC §5a), read as guard reads them, so an inherited field cannot make
// data look marked. Python's twin makes the same judgement on {'value', 'meta'}.
function isMarked(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value) || !Object.hasOwn(value, "value"))
    return false;
  const proto = Object.getPrototypeOf(value);
  if (proto !== Object.prototype && proto !== null) return false;
  const own = Object.entries(metaOf(value)).filter(([key]) => Object.hasOwn(value, key));
  return validateEnvelope(Object.assign(Object.create(null), Object.fromEntries(own))).length === 0;
}

/**
 * Marks a fixture's value `source: "mock"` (#123). A value that is already
 * marked is refused: marking it again would nest it, and marking a value
 * someone labelled `real` as mock would hide that label.
 * @param {*} value - The fixture's raw value
 * @returns {object} The value, marked mock
 * @throws {TypeError} when `value` is already marked
 */
export function markFixture(value) {
  if (isMarked(value))
    throw new TypeError("markFixture: the fixture returned a marked value; pass the raw value and let it be marked mock");
  return mark(value, { source: "mock" });
}

// guard's verdict: null when the value may leave, else its refusal.
function verdict(output) {
  try {
    guard(output);
    return null;
  } catch (e) {
    if (e instanceof ProvenanceRefused) return e;
    throw e;
  }
}

const isMock = (refusal) => refusal.reasons.some((r) => r.startsWith("mock:"));

// Why `output` does not prove mock taint reached it, or null when it does.
function notTainted(output) {
  const refusal = verdict(output);
  if (refusal === null) return "guard let it through";
  return isMock(refusal) ? null : `guard refused it, but not for mock taint: ${refusal.message}`;
}

/**
 * Fails unless `output` may leave through an output point: guard(output)
 * with its defaults (#120). Throws an Error listing guard's reasons; returns
 * nothing.
 * @param {*} output - A marked golden output
 * @throws {Error} when mock taint (or an unmarked or malformed value) reaches it
 */
export function assertNoTaint(output) {
  const refusal = verdict(output);
  if (refusal !== null) throw new Error(`${NO_TAINT}: ${refusal.message}`);
}

/**
 * Fails unless guard refuses `output` for mock taint: the claim that a
 * fixture's taint reached it, verified. A value guard refuses for another
 * reason (unmarked, malformed) is not proof, and fails.
 * @param {*} output - A marked value expected to carry mock taint
 * @throws {Error} when guard lets it through, or refuses it for another reason
 */
export function assertTainted(output) {
  const why = notTainted(output);
  if (why !== null) throw new Error(`${TAINTED}: ${why}`);
}

/**
 * Matchers for `expect.extend(plumbMatchers)`. `expect(x).toBeUntainted()` is
 * assertNoTaint; `.not.toBeUntainted()` is assertTainted: it passes only when
 * guard refuses for mock taint, never for a value refused for another reason.
 */
export const plumbMatchers = {
  toBeUntainted(received) {
    if (this?.isNot) {
      // Negated: vitest passes the assertion when `pass` is false.
      const why = notTainted(received);
      return why === null
        ? { pass: false, message: () => "expected mock taint, and it is there" }
        : { pass: true, message: () => `${TAINTED}: ${why}` };
    }
    const refusal = verdict(received);
    return refusal === null
      ? { pass: true, message: () => `${TAINTED}: guard let it through` }
      : { pass: false, message: () => `${NO_TAINT}: ${refusal.message}` };
  },
};
