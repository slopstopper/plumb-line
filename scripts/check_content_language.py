#!/usr/bin/env python3
"""check_content_language — flag language-standard violations in a content draft.

Gate 2 of the release-to-content routine (docs/content/TEMPLATE.md, GH #255).
A FLAGGER, deliberately not a CI gate: it prints file:line + the matched
pattern and always exits 0 unless invoked with --strict. The decision stays
with the human reviewer — banning strings in CI would invite synonym evasion
and false confidence, which is the project's own laundered-uncertainty defect
(decision recorded 2026-08-15, superseding the site's removed "CI fails any
README containing battle-tested" claim).

Matches per paragraph, not per physical line, so a construction split across
a hard wrap is still seen (#316); the reported line is where the match starts.

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
    # re.M: matched per paragraph now, and a heading is not always preceded
    # by a blank line, so `^` must mean line start, not paragraph start.
    ("emoji header", re.compile(r"^#{1,6}\s*[^\w\s`\[#]", re.U | re.M)),
    ("roll-on emphasis tail", re.compile(r",\s*and\s+(?:it|that)\s+(?:matters|shows|counts)\b", re.I)),
    ("register: quiet part", re.compile(r"\bquiet part\b", re.I)),
    ("bare contrast (X, not Y / not X but Y)",
     re.compile(r",\s*not\s+\w|\bnot\s+(?:by\s+|a\s+|an\s+|the\s+)?[\w-]+(?:\s+[\w-]+){0,3}\s+but\b", re.I)),
]

# Em dashes are counted, not flagged: kept to a bare minimum by owner ruling
# (2026-08-18), but a hard flag would contradict allowing any at all.
_EM_DASH = "—"


def em_dashes(path):
    with open(path, encoding="utf-8") as f:
        return f.read().count(_EM_DASH)


def _paragraphs(lines):
    """Yield (first_line_number, [lines]) per blank-line-separated paragraph."""
    start, buf = None, []
    for n, line in enumerate(lines, 1):
        if line.strip():
            if start is None:
                start = n
            buf.append(line.rstrip("\n"))
        elif buf:
            yield start, buf
            start, buf = None, []
    if buf:
        yield start, buf


def check(path):
    """(line, label, text) per match, in file order.

    Patterns are matched against each PARAGRAPH with its hard wraps kept as
    newlines — every pattern's whitespace class already crosses a newline, so
    a construction split across a wrap ("verified by import, / not by
    execution") is seen without any pattern changing (#316: per-physical-line
    matching let exactly that escape, and the test suite pinned the miss). A
    blank line ends the paragraph, so a sentence in the next paragraph is not
    joined to this one. The reported line is where the match STARTS; `text`
    covers every physical line the match spans, joined with single spaces.
    """
    flags = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for start, para in _paragraphs(lines):
        text = "\n".join(para)
        for label, pat in PATTERNS:
            for m in pat.finditer(text):
                first = start + text.count("\n", 0, m.start())
                last = start + text.count("\n", 0, m.end())
                shown = " ".join(ln.strip() for ln in para[first - start:last - start + 1])
                flags.append((first, label, shown))
    # File order, stable within a line (pattern order) — the shape the
    # per-line scan produced, so reports diff cleanly against old ones.
    flags.sort(key=lambda flag: flag[0])
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
    dashes = em_dashes(args[0])
    if dashes:
        print(f"{args[0]}: {dashes} em dash(es) - informational, keep to a bare minimum")
    print(f"\n{len(flags)} flag(s). A flag is a prompt to reread, not a verdict.")
    return 1 if (strict and flags) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
