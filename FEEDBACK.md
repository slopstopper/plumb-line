# Sharing feedback

plumb-line gets better with real use cases — especially the awkward ones. Two ways to send feedback, depending on whether it's shareable.

## Public — a GitHub issue

Open the **[Feedback / use case](https://github.com/effythealien/plumb-line/issues/new?template=feedback.yml)** form. Good for bugs, false positives, "ran it, found nothing", and use cases you're happy to share in the open.

## Private — for sensitive or internal codebases

Testing on a private codebase you can't describe in a public issue? Send it privately instead:

**Private feedback form: [https://formspree.io/f/mwvdqwpe](https://formspree.io/f/mwvdqwpe)**

This is for the most valuable kind of feedback — a concrete "it caught something we'd otherwise have shipped" from a real, confidential codebase. It goes only to the maintainer.

## What helps most

- **Raw output over summaries** — paste the actual lint output, stack traces, audit findings.
- **One concrete example** — a value that was un-provenanced, mock-leaked, or confidently-wrong that plumb-line surfaced (before → after).
- **False positives** — anywhere the lint flagged honest code. These directly improve the rules.

Either channel: let me know if I may quote you or name you as an early user.
