# Architecture Decision Records

This directory records the **durable decisions** behind plumb-line — what was
chosen, why, and what it costs — so a future reader (or contributor) can
understand the shape of the project without reconstructing it from the code.

ADRs are the published record. The rougher working notes that produced them —
design specs and implementation plans under `docs/specs/` and `docs/plans/` —
are kept local and unpublished by design (see [ADR-0006](0006-build-docs-strategy.md)).

## Format

Each ADR uses a lightweight [MADR](https://adr.github.io/madr/)-style structure:
**Status · Context · Decision · Consequences**. An ADR captures a decision and
its trade-offs, not implementation detail — that is what lets it outlive any one
build.

A decision, once recorded, is not edited away. If a later decision overturns an
earlier one, the earlier ADR stays and is marked `Superseded by ADR-NNNN`; the
record is append-only.

## Index

| ADR                                                     | Title                                                     | Status   |
| ------------------------------------------------------- | --------------------------------------------------------- | -------- |
| [0001](0001-domain-neutral-by-construction.md)          | Domain-neutral by construction                            | Accepted |
| [0002](0002-packaged-as-a-collection.md)                | Packaged as a skill collection, not one skill             | Accepted |
| [0003](0003-two-enforcement-adapters-at-v1.md)          | Two real enforcement adapters at v1 (JS + Python)         | Accepted |
| [0004](0004-enforcement-parameterized-no-defaults.md)   | Enforcement is parameterized and ships nothing by default | Accepted |
| [0005](0005-provenance-primitive-one-law-two-layers.md) | Provenance primitive: one law, two layers                 | Accepted |
| [0006](0006-build-docs-strategy.md)                     | Build docs stay private; decisions are published          | Accepted |
| [0007](0007-branch-guard-hardening.md)                  | Branch-guard allowlist hardening                          | Accepted |
