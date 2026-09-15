# plumb-line Python adapter

`provenance_lint.py` is the Python parity checker to the JS
`no-provenance-bypass` / `require-provenance-output` ESLint rules — the
stdlib-`ast` complement to the runtime `audit_meta()`, flagging PB1–PB4 and
(with `--require-output`) untagged outputs on a declared surface. See its
module docstring for usage, and [ADR-0011](../../docs/adr/0011-enforcement-rule-scoping.md)
for the output-tagging design.

Each REQ-OUTPUT issue carries `"symbol"`, the module-level function name —
the site identity the Action's ratchet keys on.
