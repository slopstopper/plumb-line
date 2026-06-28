# ADR-0004: Enforcement is parameterized and ships nothing by default

**Status:** Accepted · 2026-06-28

## Context

The `plumb-line-bootstrap` skill installs enforcement into a target repository:
the boundary check, the gates, the branch guard. To do that it needs to know the
project's layers, their dependency direction, and the one allowed exception (the
composition root).

The tempting shortcut is to ship sensible defaults — a stock set of layers and
paths that "most projects" have. But plumb-line's whole thesis is epistemic
honesty: a tool that _guesses_ a project's source-truth layer and writes it into
enforced config would be inventing structure the builder never confirmed —
exactly the kind of unprovenanced claim the project exists to prevent. It would
also re-import the origin domain's assumptions through the back door, violating
[ADR-0001](0001-domain-neutral-by-construction.md).

## Decision

Bootstrap **derives structure from the builder, and never assumes it.** It:

1. detects the project language and selects the adapter,
2. interviews the builder via the principles' "find your version" prompts,
3. generates a filled, domain-neutral ruleset from the template,
4. installs the adapter's enforcement parameterized to the builder's
   layers/paths/direction.

It ships **no default layers and invents no answers.** If the builder cannot name
their source-truth layer, _that is the finding_ — the skill surfaces it rather
than fabricating one. plumb-line eats its own dog food: it refuses to launder an
unknown into a confident default.

## Consequences

- Enforcement is genuinely portable: adapters take layer names, paths, and
  direction as generated config, with no hardcoded source paths.
- The tool can produce a _finding instead of an artifact_ — a legitimate,
  first-class outcome consistent with "a null result is valid." Bootstrap is
  allowed to conclude "you don't yet have a definable source-truth layer."
- The cost is more work up front for the builder (an interview, not a one-click
  install) and more careful skill design (the skill must handle "I don't know"
  gracefully rather than filling the blank).
