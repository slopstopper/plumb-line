# ratchet-adoption-js — the provenance ratchet over a legacy **JS** surface (#393)

The JS twin of `examples/ratchet-adoption`. Same shape, same contract, other
language: this one is what proves the JS half of the ratchet — the rule's
`[site: name]` message suffix, the SARIF assembler's `SITE_RE` extraction, and
`ratchet.apply` over real ESLint output — end to end through the Action, rather
than by unit tests over recorded ESLint JSON.

Two trees with **identical source** and different ratchet files.

- `clean/` pins both untagged outputs in `src/pricing/fx.js`. The Action
  reports them as `note`-level `PL/untagged-output` results ("known
  (ratchet): …") and exits 0 under `fail-on: findings`.
- `broken/` pins only `applyFx`. `total` is a **new** untagged output: an
  `error`, the job fails under `fail-on: findings`, and the message says how
  to accept it.

## What each run must report

Run from the repo root, after the install step below:

```sh
python3 adapters/sarif/run_checks.py --root examples/ratchet-adoption-js/<tree> \
    --manifest .plumb-line/enforcement.json --scripts-dir . \
    --fail-on findings --sarif /tmp/pl.sarif --summary /tmp/pl.json --version dev
```

| tree | known | new | stale | unmeasured | findings | exit (`fail-on: findings`) | exit (`fail-on: none`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `broken` | 1 | 1 | 0 | `[]` | 1 | 1 | 0 |
| `clean` | 2 | 0 | 0 | `[]` | 0 | 0 | 0 |

`unmeasured` must be `[]` in both: a ratchet over a surface nothing ran on is
a claim nobody checked, and `state: "ran"` alone cannot catch globs that
stopped matching (#395).

Both trees enforce `js.provenance` as well as `js.output` — the manifest's
`provenance` block carries `globs` (required) and `outputGlobs`, so the runner
derives both capabilities from it. `js.provenance` reports 0 results: the only
rule the config enables is `require-provenance-output`, whose findings belong
to `js.output`.

## The toolchain step

`eslint-provenance.cjs` reaches `adapters/js/provenance-lint/index.cjs` by
relative path — the plugin is never installed — but **ESLint itself is the
consumer's own**, found by walking up from the root for
`node_modules/.bin/eslint`. So each tree carries a `package.json` +
`package-lock.json` and needs an install before the Action or the runner can
see the surface at all:

```sh
(cd examples/ratchet-adoption-js/broken && npm ci --no-audit --no-fund)
(cd examples/ratchet-adoption-js/clean  && npm ci --no-audit --no-fund)
```

This is what `examples/js-payments-service` already does: CI's Action job
installs it in the "consumer toolchain" step, and CI's Python job installs it
in the "JS fixture toolchain" step so the end-to-end SARIF test runs instead of
skipping. Without the install the capability is `tool-missing`, which fails the
job — it never reads as clean.

## Regenerating the ratchet files

```sh
python3 adapters/sarif/ratchet.py update --root examples/ratchet-adoption-js/clean \
    --because "initial pin: adopting the ratchet over the legacy JS pricing surface"
```

`clean/`'s file is exactly what that command wrote. Running it again over an
unchanged tree reports `nothing changed` and rewrites nothing, so the fixture
stays byte-stable. Both claims, and the shape of `broken/`'s hand edit below,
are checked by `examples/test_ratchet_fixtures.py`.

`broken/`'s file is **not** a run over `broken/`: it is `clean/`'s file with
`total` removed by hand and the reason reworded, simulating a site added
*after* adoption. No run over `broken/` could have produced it — the tree has
two sites and the file pins one; that is the whole point of the fixture, and
its `because` says so rather than letting the history imply a run that never
happened.

CI runs `uses: ./` over both trees.
