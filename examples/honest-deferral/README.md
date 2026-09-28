# Honest deferral: a test that cannot pass yet

A worked example for `plumb-line-method`'s section **Mid-task: a test that
cannot pass honestly** (#485). The scenario: a shipping quote comes from a
carrier's API, and CI has no key for the carrier's sandbox yet. The
requirement, "the standard parcel is priced at 12.40 from the carrier's rate
card", cannot be met from CI, for a reason outside the code.

What the example does, in both languages:

1. **It handles the failure CI can observe.** An unreachable carrier gives a
   quote with status `unavailable` and no price, never an invented one. A
   normal test proves it.
2. **It keeps the requirement's test, assertion unchanged,** and marks it as
   a strict expected failure with its reason:
   - Python: `@pytest.mark.xfail(strict=True, reason="…")` in
     `python/test_carrier.py`;
   - JavaScript: `it.fails("…", …)` (vitest) in `js/carrier.test.js`, with the
     reason in the comment above it.
3. **Strict means it cannot outlive its reason.** The moment the carrier
   becomes reachable and the test passes, the marker fails the suite, and
   the deferral has to be removed on purpose.

`EXAMPLE-1` stands for the tracked issue; a real deferral cites a real one.
The fourth condition is not in the code, it is in the handover: the agent's
final message says the requirement is **not met**, that accepting or
reversing the deferral is the owner's call, and does not present the green
suite as done. The method skill gives the wording.

Not a deferral: `pytest.mark.skip`, `skipif`, `xfail` without `strict=True`,
`it.skip`, `it.todo`, a commented-out test, a rewritten assertion, or a mock
of the carrier in the requirement's test. Each makes CI green by making it
stop checking.

## The proof

`examples/test_honest_deferral.py` runs each suite in a copy and checks both
properties: as shipped, one test passes and the requirement's test is
recorded as an expected failure; with the carrier made reachable (a patch in
the copy only), the suite fails on the strict marker.

```sh
python3 -m pytest -q examples/test_honest_deferral.py
cd examples/honest-deferral/js && npm ci   # for the JS half
```
