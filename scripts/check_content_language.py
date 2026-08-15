#!/usr/bin/env python3
"""check_content_language — flag language-standard violations in a content draft.

Gate 2 of the release-to-content routine (docs/content/TEMPLATE.md, GH #255).
A FLAGGER, deliberately not a CI gate: it prints file:line + the matched
pattern and always exits 0 unless invoked with --strict. The decision stays
with the human reviewer — banning strings in CI would invite synonym evasion
and false confidence, which is the project's own laundered-uncertainty defect
(decision recorded 2026-08-15, superseding the site's removed "CI fails any
README containing battle-tested" claim).

Usage: python3 scripts/check_content_language.py <draft.md> [--strict]
"""
import re
import sys

# Each entry: (label, compiled pattern). Small on purpose — a phrase earns its
# place by actually appearing in a draft, not by speculation.
PATTERNS = [
    ("not-X-but-Y construction",
     re.compile(r"\b(?:it['’]?s|it is|this is)\s+not\s+(?:just\s+)?\w[^.;:]{0,40}[,;]\s*(?:it['’]?s|it is|but)\b", re.I)),
    ("register: delve", re.compile(r"\bdelv(?:e|ing|es)\b", re.I)),
    ("register: landscape (figurative)", re.compile(r"\blandscape\b", re.I)),
    ("register: unlock (figurative)", re.compile(r"\bunlock(?:s|ing|ed)?\b", re.I)),
    ("register: game-changer", re.compile(r"\bgame[- ]chang(?:er|ing)\b", re.I)),
    ("hollow superlative", re.compile(r"\b(?:blazingly|incredibly|revolutionary|cutting[- ]edge|state[- ]of[- ]the[- ]art|world[- ]class|seamless(?:ly)?|effortless(?:ly)?)\b", re.I)),
    ("unverifiable maturity claim", re.compile(r"\bbattle[- ]tested\b|\bproduction[- ](?:proven|grade|ready)\b", re.I)),
    ("emoji header", re.compile(r"^#{1,6}\s*[^\w\s`\[]", re.U)),
    ("roll-on emphasis tail", re.compile(r",\s*and\s+(?:it|that)\s+(?:matters|shows|counts)\b", re.I)),
]


def check(path):
    flags = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            for label, pat in PATTERNS:
                if pat.search(line):
                    flags.append((lineno, label, line.rstrip()))
    return flags


def main(argv):
    args = [a for a in argv[1:] if a != "--strict"]
    strict = "--strict" in argv
    if len(args) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    flags = check(args[0])
    for lineno, label, line in flags:
        print(f"{args[0]}:{lineno}: [{label}] {line}")
    if not flags:
        print(f"{args[0]}: no language-standard flags")
    print(f"\n{len(flags)} flag(s). A flag is a prompt to reread, not a verdict.")
    return 1 if (strict and flags) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
