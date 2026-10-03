# ADR-0022: Keep the code honest in tiers: enforcement where it can, accurate labels, and auditability for the rest

**Status:** Accepted · 2026-10-03 (drafted from the owner's words on GH #462 and #623; text approved by the owner, recorded on #462)

## Context

Plumb-line keeps code honest about itself in more than one way: some
mechanisms block, some require a label, and some make things visible to
review. Until now nothing said how they relate. The impossible-task spike
(#462) showed what each one can and cannot do.

- **A block can push honest work aside.** The pre-commit gate blocked every
  red commit on every branch. In round 3b, honest red work stayed
  uncommitted, and 23 of 30 bootstrapped runs named `--no-verify` as the way
  round (none used it). The gate was made branch-aware (#613): it still blocks
  on `main`, and on other branches it lets a red commit through with a
  notice. After that, 9 of 15 honest runs committed their red work on a
  branch, and nothing reached `main`. It had a cost: arm C's honest rate fell
  from 80% to 60%, which trips the pre-registered threshold. Three runs made
  the requirement test skip itself; with three runs, the cause is unknown
  (#621).
- **Some things cannot be forbidden without breaking ordinary work.** A
  stubbed dependency in a unit test is everyday practice. The spike's agents
  used stubs honestly, and also to fake a result. The method-skill fix (#623)
  kept stubs and forbade presenting them as real, by label or by value.
  Among runs that loaded the method skill, fake-as-real tests went from 6 of
  6 to 0 of 6. One run that did not load it still faked, with a stub labelled
  `mock` whose value reproduced the requirement's.
- **What is neither blocked nor labelled has to be seen.** The audit caught
  every cheat that changed the requirement test, and missed every stub that
  claimed too much (#620).

## Decision

The owner, 2026-10-03, on #462:

> "So my thinking is ultimately we can't restrict the stub test completely,
> but we can make sure that it's accurately labeled. Because I think if we
> restricted it completely and made that the rule, it would make it
> impossible to work with from an actual usability standpoint. So while
> Plumline can prevent some things from happening accidentally, when placed
> in a, an impossible situation like the impossible spike, the best thing it
> can do is make sure that everything's labeled accurately. Because that
> follows the plumb line principle at its core."

> "I'm always thinking like a bit of a tier system. Ultimately, Plumline's
> going to try and keep the code honest. And sometimes that will be via
> enforcement. But mostly it makes it just makes it auditable."

So plumb-line keeps code honest in three tiers.

1. **Enforcement,** which prevents some things from happening accidentally,
   where a block does not make ordinary work impossible. Current examples:
   - the branch guard on protected branches;
   - the pre-commit gate on protected branches;
   - the boundary guard, against an import that runs against the declared
     layer direction (P2 — One-way layering);
   - constructors refusing values off the ladder (ADR-0019);
   - the egress guard, refusing mock data at an output (ADR-0020).
2. **Accurate labels,** where a ban would make ordinary work impossible.
   Stand-ins, fixtures, fallbacks and deferrals stay possible, and they are
   labelled for what they are:
   - a fixture opted into quarantine is marked `mock` (P4 — Quarantined
     fakery, ADR-0021);
   - a test of a stand-in below the point where the code marks its sources
     makes no claim about provenance, and nothing fake is presented as real,
     by label or by value (#623);
   - a deferral is a strict marker with its reason (#485).
3. **Auditability** for everything else, which is most of it. Provenance and
   lineage on values, the gate's notices, the audit skill and the records
   make the rest visible to review.

## Operating rules

These two were drafted with this ADR, not taken from the owner's words, and
the owner accepted them one by one on 2026-10-03:

- **(a) Tier per check** (accepted). A new check says which tier it is in, and why not
  the one above. The tier is named per check, not per mechanism: the gate's
  test results block on a protected branch and are audit-only elsewhere
  (where it still blocks a configuration error).
- **(b) The enforcement test** (accepted for v0.13.0). Enforce only where
  every honest outcome has a route the block allows, and the block's message
  names it: a branch, the docs allowlist (ADR-0007), or a strict
  expected-failure marker. #613 added such a route for red work, a feature
  branch, and the gate's message names it. The other enforcement examples
  above are to be checked against it in v0.13.0 (#630); only the gate's is
  checked so far.

## Consequences

- **The v0.12.0 changes from the spike fit the tiers.** #613 kept
  enforcement on protected branches and made other branches auditable, at the
  measured cost above. #623 tightened a label without adding a block.
- **The auditability tier's known gaps:**
  - the audit misses a stub test that claims to be real (#620);
  - an unchecked or red commit leaves no durable record (#626).
- **This changes no principle** in `reference/portable-principles.md`. It
  records how plumb-line uses its mechanisms to keep code honest, not what
  the principles are.
