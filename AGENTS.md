# AGENTS.md — plumb-line

Instructions for coding agents working in this repository. Humans want
[`CONTRIBUTING.md`](CONTRIBUTING.md) (how to contribute),
[`DEVELOPMENT.md`](DEVELOPMENT.md) (how to build and test), and
[`ROADMAP.md`](ROADMAP.md) (what is planned) — this file does not repeat them.

Two things are load-bearing here and easy to get wrong:

**This repo is held to its own principles.** The
[portable principles](reference/portable-principles.md) that the audit skill
applies to other people's code apply to this code. Don't launder uncertainty,
hardcode a prior, or overstate maturity — use the maturity vocabulary
(`current` / `planned`), not aspirational claims.

**There is no root test command.** Each component is tested from its own
directory; see [`DEVELOPMENT.md`](DEVELOPMENT.md).

## Tracking (recursive-spine convention)

Work state lives in GitHub issues and milestones, not in prose files.
- What's in flight: `gh issue list --assignee @me`
- Deferred work: `gh issue list --label audit-deferral`
- Branches: `<prefix>/<issue>-<slug>`; PRs say `Closes #N`.
- Deferral requires a filed issue. Handover files its debts before closing.
Dialect and modules for this repo: [docs/tracking-dialect.md](docs/tracking-dialect.md)

Two local rules go beyond the convention's baseline, both from
[`ROADMAP.md`](ROADMAP.md):

- **Every open issue carries exactly one** of a release milestone
  (= scheduled) or a `track:*` label (= deliberately unscheduled). Neither
  is a tracking bug, not a backlog item.
- **Deferrals have an outbox.** At each release-scoping moment, every open
  `audit-deferral` older than 30 days is either scheduled into the next
  release or closed with a written waiver. No third option.
