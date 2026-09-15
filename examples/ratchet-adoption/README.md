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

Both files were written by that command (date pinned by hand so the fixture
is stable). CI runs `uses: ./` over both trees.
