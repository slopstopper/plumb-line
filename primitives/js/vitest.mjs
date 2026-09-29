// vitest.mjs — the fixture quarantine for vitest (#123), on the
// `plumb-line-provenance/vitest` subpath. Tests are where fake data is
// supposed to live; this makes the quarantine explicit there. markFixture
// marks a fixture's value `source: "mock"`, so anything derived from it
// carries the taint; assertNoTaint and the toBeUntainted matcher fail a test
// when a golden output still carries it.
//
// Owner decisions on #123: marking is opt-in per fixture; the check takes a
// marked value only (#544). The check is the egress guard (#120, SPEC §5c)
// with its defaults. This module never imports vitest: register the matcher
// with `expect.extend(plumbMatchers)`. Python twin: pytest_plugin.py.
import { mark } from "./marked.mjs";
import { guard, ProvenanceRefused } from "./guard.mjs";

const PREFIX = "no mock taint may reach a golden output";

function isMarked(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) && Object.hasOwn(value, "value");
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

// guard's verdict as text: null when the value may leave, else the refusal.
function refusal(output) {
  try {
    guard(output);
    return null;
  } catch (e) {
    if (e instanceof ProvenanceRefused) return e.message;
    throw e;
  }
}

/**
 * Fails unless `output` may leave through an output point: guard(output)
 * with its defaults (#120). Throws an Error listing guard's reasons; returns
 * nothing.
 * @param {*} output - A marked golden output
 * @throws {Error} when mock taint (or an unmarked or malformed value) reaches it
 */
export function assertNoTaint(output) {
  const refused = refusal(output);
  if (refused !== null) throw new Error(`${PREFIX}: ${refused}`);
}

/**
 * Matchers for `expect.extend(plumbMatchers)`: `expect(x).toBeUntainted()`
 * is assertNoTaint as a matcher; `.not.toBeUntainted()` expects the refusal.
 */
export const plumbMatchers = {
  toBeUntainted(received) {
    const refused = refusal(received);
    return refused === null
      ? { pass: true, message: () => "expected the value to carry mock taint, but guard let it through" }
      : { pass: false, message: () => `${PREFIX}: ${refused}` };
  },
};
