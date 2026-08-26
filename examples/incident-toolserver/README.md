# Incident reconstruction — the server that reported success for dead tools

> The full postmortem write-up for this reconstruction is at
> [`docs/postmortems/mock-toolserver.md`](../../docs/postmortems/mock-toolserver.md).

**This is a reconstruction modeling a failure class, not any project's actual
code.** The class: stub tools returning success-shaped payloads that
downstream reporting aggregates into real-looking status. A widely discussed
public instance is claude-flow issue
[ruvnet/ruflo#653](https://github.com/ruvnet/ruflo/issues/653) ("85% of MCP
Tools Are Mock/Stub Implementations"), whose own numbers were then disputed —
[40% by follow-up analysis](https://github.com/ruvnet/claude-flow/issues/658),
"99% theater" by a
[third-party audit](https://gist.github.com/roman-rr/ed603b676af019b8740423d2bb8e4bf6).
Three audits of the same codebase produced three different numbers for how much
of it was fake, because mockness was not machine-readable. No code from that
project appears here; the tools below are synthetic.

## The demo

Two variants of a five-tool server where three tools are stubs. Same tools,
same aggregation, one difference.

**Broken** — no provenance. The report is green and says nothing else:

```sh
node broken/toolserver.mjs
```

**Instrumented** — each tool result is `mark`ed with its honest source when
produced; the report is `derive`d under the combination law:

```sh
node instrumented/toolserver.mjs
```

The instrumented report still says `operational (5/5 tools succeeded)` — the
stubs did return success — but its envelope carries `derivedFromMock: true`,
`weakestSource: mock`, and the mock fraction as a computed property of lineage
(`3/5`), not a forensic estimate. The final section attempts the escape hatch
(re-deriving the report with `source: "real"`): `auditMeta` flags it as
laundering, because taint cannot be overridden away.

## The review-time half

The runtime library is one half of plumb-line. The other half needs no
integration at all: point `plumb-line-audit` at `broken/` and the audit flags
success-shaped stubs feeding a reporting path (see `VIOLATIONS.md` in
`broken/` for the answer key). That is the adoption order the demo suggests —
audit first, zero commitment; the primitive when you want the same honesty
enforced while the code runs.

## Scope

A minimal shape-demonstrator (~50 and ~100 lines): no real server, no network,
no dependencies beyond the Node standard library and the in-repo primitive.
The integrity test (`test_demo.py`) runs both scripts and locks the behavioral
markers — broken stays silent about mocks, instrumented confesses, the launder
attempt is flagged.
