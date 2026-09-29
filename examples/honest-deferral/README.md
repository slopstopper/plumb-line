# Honest deferral: a test that cannot pass yet

A worked example for `plumb-line-method`'s section **Mid-task: a test that
cannot pass honestly** (#485). The scenario: a shipping quote comes from a
carrier's API, and CI has no key for the carrier's sandbox yet. The
requirement, "the standard parcel is priced at 12.40 from the carrier's rate
card", cannot be met from CI, for a reason outside the code.

What the example does, in both languages:

1. **It handles the failure CI can observe.** Without a key the carrier
   cannot be asked, and the quote says `unavailable` with no price, never an
   invented one; an answer with no price is `unavailable` too. A normal test
   proves it against the real code, with the key unset.
2. **It keeps the requirement's test, assertion unchanged,** and marks it as
   a strict expected failure with its reason:
   - Python: `@pytest.mark.xfail(strict=True, raises=AssertionError,
     reason="…")` in `python/test_carrier.py`. `raises=AssertionError` means
     only the unmet assertion counts as expected; a crash does not.
   - JavaScript: `it.fails("deferred (EXAMPLE-1): <reason> …", …)` (vitest)
     in `js/carrier.test.js`, the reason in the title, the marker itself (the
     default reporter prints counts only; a verbose or junit report prints
     the title). `it.fails` accepts any error, which is why the
     observable-failure test in step 1 has to exist: it is what catches a
     crash.
3. **Strict means it cannot outlive its reason.** The moment the carrier
   becomes reachable and the test passes, the marker fails the suite, and
   the deferral has to be removed on purpose.

`EXAMPLE-1` stands for the tracked issue; a real deferral cites a real one.
The fourth condition is not in the code, it is in the handover: the agent's
final message says the requirement is **not met**, that accepting or
reversing the deferral is the owner's call, and does not present the green
suite as done. The method skill gives the wording.

Not a deferral: `pytest.mark.skip`, `skipif`, `xfail` without `strict=True`
(unless the project's pytest config makes xfail strict by default),
`xfail(run=False)`, an
imperative `pytest.xfail()`, `it.skip`, `it.todo`, a commented-out test, a
rewritten assertion, or a mock of the carrier in the requirement's test.
Each makes CI green by making it stop checking.

## The proof

`examples/test_honest_deferral.py` runs each suite in a copy and checks
three properties, in both languages:
- as shipped, the missing-key test passes and the requirement's test is
  recorded as an expected failure;
- with the carrier made reachable (in the copy only: the key set and the
  request answered), the suite fails on the strict marker while the
  missing-key test still passes;
- with the code broken to crash on the missing key, the suite fails: in
  Python because `raises=AssertionError` refuses the crash, in JS because
  the missing-key test fails (`it.fails` itself absorbs any error);
- the JS reason, in the marker's title, shows in a verbose report (the
  default reporter prints counts only).

```sh
python3 -m pytest -q examples/test_honest_deferral.py
cd examples/honest-deferral/js && npm ci   # for the JS half
```
