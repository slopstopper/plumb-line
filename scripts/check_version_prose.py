#!/usr/bin/env python3
"""Gate: no live documentation may state a wire version other than the current
PROVENANCE_VERSION.

The envelope wire version is restated in prose across the docs. The v0.7.0 bump
moved it 1->2 in the manifests and SPEC.md but left seven prose copies stale,
caught only by a human dogfood pass (issue #160). This makes that check
mechanical.

The gate recognises three CANONICAL FORMS. A doc that states the wire version
uses one of them; the checker does not try to parse every possible phrasing,
because a regex broad enough to catch all of them produces false positives on
ordinary prose. If a doc needs a new way to say it, add the form here.

Pure stdlib - no pytest, no third party - so it can run in CI before test deps
are installed. Run from the repo root:

    python3 scripts/check_version_prose.py
"""
import os
import re
import subprocess
import sys
from collections import namedtuple

Finding = namedtuple("Finding", "path line_no found expected line_text")

MARKER = "<!-- wire-version-historical -->"

# Append-only historical records. These are SUPPOSED to say version 1 forever;
# rewriting them would falsify the history they exist to preserve.
EXEMPT_PREFIXES = (
    "CHANGELOG.md",
    "docs/adr/",
    "docs/dogfood.md",
    "docs/validation-results.md",
)

_PATTERNS = (
    re.compile(r"schema version (\d+)"),
    re.compile(r"plumb-line[_ ]v(\d+)"),
    re.compile(r"PROVENANCE_VERSION.{0,12}?(\d+)"),
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_current_version(text):
    """Parse PROVENANCE_VERSION out of primitives/python/provenance.py source."""
    m = re.search(r"^PROVENANCE_VERSION\s*=\s*(\d+)", text, re.M)
    if not m:
        raise ValueError("PROVENANCE_VERSION not found in provenance source")
    return int(m.group(1))


def is_exempt_path(path):
    return path.startswith(EXEMPT_PREFIXES)


def exempt_line_numbers(lines):
    """1-indexed line numbers exempted by an inline marker.

    The marker exempts the line it sits on. When it is alone on its own line it
    exempts the nearest preceding non-blank line instead, so a wrapped markdown
    bullet can be tagged without a trailing comment mid-sentence.
    """
    exempt = set()
    for i, line in enumerate(lines):
        if MARKER not in line:
            continue
        exempt.add(i + 1)
        if line.strip() == MARKER:
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0:
                exempt.add(j + 1)
    return exempt


def scan_text(path, text, current):
    """Return a Finding for every canonical-form match whose version != current."""
    findings = []
    lines = text.splitlines()
    exempt = exempt_line_numbers(lines)
    for line_no, line in enumerate(lines, start=1):
        if line_no in exempt:
            continue
        for pattern in _PATTERNS:
            for m in pattern.finditer(line):
                found = int(m.group(1))
                if found != current:
                    findings.append(Finding(path, line_no, found, current, line.strip()))
    return findings
