# Governance

This document describes how plumb-line is governed: how decisions are made, the
roles people play, and how access and continuity are maintained. It is
deliberately lightweight — the project is small — but explicit, so contributors
know what to expect and the project can survive changes in who runs it.

## Project status and model

plumb-line is currently a **single-maintainer project** under a
*benevolent-maintainer* model. The maintainer is responsible for the direction
of the project, reviews and merges changes, and cuts releases. This is stated
plainly rather than dressed up as a committee: the honesty the tool enforces on
code applies to its own governance.

The model is intended to grow. As additional regular contributors appear, the
project will move toward shared maintainership (see
[Becoming a maintainer](#becoming-a-maintainer)); this document will be updated
to match reality rather than aspiration.

## How decisions are made

- **Everyday changes** (bug fixes, tests, docs, dependency bumps) are decided by
  normal review: open a pull request, a maintainer reviews and merges. See
  [CONTRIBUTING.md](CONTRIBUTING.md) for what a mergeable PR looks like.
- **Design changes and new features** are discussed in a
  [GitHub issue](https://github.com/effythealien/plumb-line/issues) *before*
  code is written, so the direction is agreed before anyone invests effort.
- **Durable architectural decisions** are recorded as
  [ADRs](docs/adr/). ADRs are append-only: a superseded decision is marked as
  superseded, not deleted, so the reasoning stays legible over time.
- **Changes to the enforced principles** — the
  [portable principles](reference/portable-principles.md) and the behaviour of
  the primitives, adapters, and skills — get extra scrutiny and, when the
  method surface changes, run through the
  [release harness](docs/release-harness.md) (blind validation + dogfood
  self-audit) before a release.

When there is disagreement, the maintainer decides, with the reasoning recorded
in the issue, PR, or an ADR. Decisions are made in the open on GitHub.

## Roles and responsibilities

**Users** — anyone using the library, skills, or adapters. Users can file
issues, ask questions, request features, and report vulnerabilities (see
[SECURITY.md](SECURITY.md)). No permissions required.

**Contributors** — anyone who opens a pull request or issue. Contributors are
expected to follow [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Contributions are accepted under
Apache-2.0 (inbound = outbound; see CONTRIBUTING § *License of contributions*).

**Maintainers** — hold merge and release rights. Responsibilities:

- review and merge pull requests, and keep CI green on `main`;
- triage issues and security reports, and drive the
  [vulnerability response process](SECURITY.md);
- cut releases per [RELEASING.md](RELEASING.md);
- keep governance, roles, and access documentation current;
- uphold the Code of Conduct.

Path-level ownership is recorded in [.github/CODEOWNERS](.github/CODEOWNERS);
every PR requests review from the owner of the paths it touches.

### Becoming a maintainer

There is no bar of ceremony: a contributor who has landed several good changes,
shows sound judgement about the project's principles, and wants to take on
review/release duties can be invited to become a maintainer by an existing
maintainer. Maintainership is offered, accepted, and (if someone steps back)
relinquished in the open, and this document plus `CODEOWNERS` are updated to
match.

## Code of Conduct

Participation is governed by the [Contributor Covenant](CODE_OF_CONDUCT.md).
Enforcement is a maintainer responsibility; reports are handled as described
there.

## Access and continuity

The project is designed so it can continue with minimal interruption if the
current maintainer becomes unavailable. What holds the project together is the
Git history and the published packages — not any single person's machine or
stored secrets.

**Where authority lives**

- **Source of truth** — the Git repository at
  `github.com/effythealien/plumb-line`. Everything needed to build, test, and
  release is in the repo; there is no hidden build state.
- **Release authority** — publishing to npm and PyPI uses **OIDC trusted
  publishing** (see [RELEASING.md](RELEASING.md) and
  [release.yml](.github/workflows/release.yml)). There are **no long-lived
  registry tokens** stored in the repo or in CI secrets: the right to publish is
  bound to this repository and workflow, not to a personal credential that could
  be lost or leaked. Trusted-publisher configuration on each registry is the one
  piece of out-of-band state and can be re-established by a new owner with
  registry access.
- **Package ownership** — the npm and PyPI projects (`plumb-line-provenance`)
  and the GitHub repository are the transferable assets. Repository
  administration on GitHub controls who can merge, tag, and configure trusted
  publishing.

**Continuity plan**

- Because releases are reproducible from a tagged commit and require no personal
  secrets, a new maintainer with repository admin and registry ownership can cut
  releases without recovering anything from the previous maintainer.
- Adding or removing people with access is done through GitHub repository roles
  and the registries' collaborator/owner settings; `CODEOWNERS` and this file
  are updated to reflect the change.
- If the sole maintainer becomes permanently unavailable, the intended path is
  transfer of the GitHub repository and the npm/PyPI projects to a successor
  maintainer or trusted organization, who then re-registers trusted publishing.
  Because the project is Apache-2.0, anyone may also fork and continue it.

**Bus factor.** The project's bus factor is currently **1**. This is the honest
state and a known risk; raising it by bringing on a second maintainer is an
explicit goal (see [Becoming a maintainer](#becoming-a-maintainer)). The
no-stored-secrets release design exists specifically so that a low bus factor
does not also mean unrecoverable release infrastructure.

## Changing this document

Governance changes are made by pull request like any other change, and — when
they represent a durable decision — recorded or referenced in an ADR. This
document should always describe how the project actually works today.
