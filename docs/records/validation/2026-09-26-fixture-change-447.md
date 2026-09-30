# Fixture change between releases — 2026-09-26 (#447)

Recorded before the next harness run so its results are read against the
right fixture. `examples/js-payments-service/{broken,clean}/package.json` now
declare `"type": "module"`, matching their ESM sources; until now Node could
not load a single fixture file. `examples/ratchet-adoption-js` had the same
defect and the same fix. Nothing under `src/`, no answer key and no planted
violation changed: `test_fixture_integrity.py` still pins every marker, and
the boundary lint still flags only the planted `data → ui` import in
`broken/`. What changes for an auditor or remediator is that the sources now
load, so smoke-loading an edit no longer needs a shim. A new check,
`examples/test_js_fixture_loads.py`, imports every JS fixture source under
Node, and CI fails if it skips.

