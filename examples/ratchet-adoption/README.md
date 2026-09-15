# ratchet-adoption — the provenance ratchet over a legacy surface (#119)

Two trees with **identical source** and different ratchet files.

- `clean/` pins both untagged outputs in `src/pricing/fx.py`. The Action
  reports them as `note`-level `PL/untagged-output` results ("known
  (ratchet): …") and exits 0 under `fail-on: findings`.
- `broken/` pins only `apply_fx`. `total` is a **new** untagged output: an
  `error`, the job fails, and the message says how to accept it.

Regenerate a tree's ratchet file from the repo root with:

    python3 adapters/sarif/ratchet.py update --root examples/ratchet-adoption/clean \
        --because "initial pin: adopting the ratchet over the legacy pricing surface"

`clean/`'s file is exactly what that command wrote (date pinned by hand so the
fixture is stable); running it again over an unchanged tree reports `nothing
changed` and rewrites nothing, so the fixture stays byte-stable.

`broken/`'s file is **not** a run over `broken/`: it is `clean/`'s file with
`total` removed by hand and the reason reworded, simulating a site added
*after* adoption. No run over `broken/` could have produced it — the tree has
two sites and the file pins one; that is the whole point of the fixture, and
its `because` says so rather than letting the history imply a run that never
happened.

CI runs `uses: ./` over both trees.
