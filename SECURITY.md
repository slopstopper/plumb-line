# Security Policy

plumb-line is a tool for keeping a codebase epistemically honest. Its core
artifact — the provenance envelope — is a *trust claim*, so weaknesses in how
that claim is produced, propagated, or checked are security-relevant even when
they are not remotely exploitable. We treat them as such.

For the trust boundary itself — what the envelope does and does not guarantee,
and against whom — see [`docs/threat-model.md`](docs/threat-model.md).

## Reporting a vulnerability

**Please report privately first. Do not open a public issue for a suspected
vulnerability.**

Use GitHub's private vulnerability reporting:
**[Report a vulnerability](https://github.com/effythealien/plumb-line/security/advisories/new)**
(repository → **Security** tab → **Report a vulnerability**).

If that channel is unavailable to you, open a regular issue titled
`security: contact request` with **no technical detail**, and a maintainer will
arrange a private channel.

A useful report includes:

- the affected component (`primitives/js`, `primitives/python`, an adapter, or a
  skill) and version,
- which trust property you believe is broken — laundering, over-claim, taint
  drop, lineage tampering, or a bypass of the static lint — and
- a minimal reproduction: the smallest `mark`/`derive`/`makeMeta` (or adapter)
  sequence that produces the dishonest envelope.

## What counts as a vulnerability

In scope — a way to make the library **assert more trust than the inputs
justify**, through the documented public API:

- clearing or dropping `derivedFromMock` taint on a derived value,
- making `auditMeta` / `audit_meta` *miss* an inconsistency the SPEC says it must
  catch (an audit laxer than the combination law),
- overstating `source`, `confidence`, `confidenceScore`, or `weakestSource`
  beyond what the lineage proves,
- a source pattern that bypasses the combination law but is **not** flagged by
  the static lint within its documented scope (resolved primitive call sites,
  literal field values — see SPEC §6),
- a false *positive* in the lint that fires on honest usage (the catalogue is
  contractually zero-false-positive).

Out of scope — documented non-goals, covered in the threat model:

- mutating an envelope or payload you already hold in Python (envelopes are
  tamper-*evident*, not tamper-*proof*; the JS build freezes, Python does not),
- mutating an `unwrap`ped payload (it is returned by reference, by design),
- hand-constructing a fraudulent envelope dict/object from scratch — that is what
  `auditMeta` and the static lint exist to catch, not the constructor,
- whole-program dataflow analysis (explicitly out of scope for envelope schema
  version 1, SPEC §6).

A finding being out of scope for "vulnerability" does not mean we don't want to
hear it — open an issue or PR. It means it won't be handled under embargo.

## Supported versions

The primitives follow envelope **schema version 1** (`PROVENANCE_VERSION = 1`).
Security fixes land on the latest published minor of each package; there is no
back-port branch while the project is pre-1.0. Pin to a version and read
[`primitives/SPEC.md`](primitives/SPEC.md) for the schema contract.

| Component                       | Supported            |
| ------------------------------- | -------------------- |
| `primitives/js` (envelope v1)   | latest published     |
| `primitives/python` (envelope v1) | latest published   |
| adapters, skills                | latest `main`        |

## Disclosure

We aim to acknowledge a report within a few days, agree on an embargo window
appropriate to severity, fix under that embargo, and credit the reporter in the
advisory and changelog unless they prefer otherwise.
