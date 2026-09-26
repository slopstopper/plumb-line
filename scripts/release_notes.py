#!/usr/bin/env python3
"""release_notes — the approved write-up as the GitHub release's notes (#480).

A write-up merged with the release PR is approved (docs/content/TEMPLATE.md:
drafts only; the owner approves everything outbound). The release workflow
passes this script's output to `gh release create --generate-notes`, which
puts it above GitHub's generated notes, as the v0.11.3 piece was added by
hand. Relative links are made absolute at the release tag, so they work on
the release page and show the files as released.

Usage: release_notes.py <version> --repo OWNER/NAME --ref vX.Y.Z --out FILE [--root DIR]
Writes FILE only when the version has a write-up; exits 0 either way.
"""
import argparse
import posixpath
import re
import sys
from pathlib import Path

_LINK = re.compile(r"\]\(([^)\s]+)\)")
_EXTERNAL = ("http://", "https://", "#", "mailto:")


def find_write_up(root, version):
    """The one docs/content/*-plumb-line-<version>-*.md, or None."""
    found = sorted(Path(root, "docs", "content").glob(f"*-plumb-line-{version}-*.md"))
    if len(found) > 1:
        sys.exit(f"release_notes: more than one write-up for {version}: {[p.name for p in found]}")
    return found[0] if found else None


def absolute_links(text, repo, ref, path):
    """Rewrite each relative markdown link in `text` (a file at repo `path`)
    to https://github.com/<repo>/blob/<ref>/<resolved path>."""
    base = posixpath.dirname(path)

    def fix(m):
        target = m.group(1)
        if target.startswith(_EXTERNAL):
            return m.group(0)
        file_part, _, anchor = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(base, file_part))
        url = f"https://github.com/{repo}/blob/{ref}/{resolved}" + (f"#{anchor}" if anchor else "")
        return f"]({url})"

    return _LINK.sub(fix, text)


def build_notes(root, version, repo, ref):
    """The notes text for `version`, or None when it has no write-up."""
    piece = find_write_up(root, version)
    if piece is None:
        return None
    path = piece.relative_to(root).as_posix()
    body = absolute_links(piece.read_text(encoding="utf-8"), repo, ref, path).rstrip()
    canonical = f"https://github.com/{repo}/blob/{ref}/{path}"
    return f"{body}\n\n*Canonical copy: [{path}]({canonical}).*\n\n---\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    a = ap.parse_args(argv)
    notes = build_notes(Path(a.root), a.version, a.repo, a.ref)
    if notes is None:
        print(f"release_notes: no write-up for {a.version}; the release gets generated notes only")
        return 0
    Path(a.out).write_text(notes, encoding="utf-8")
    print(f"release_notes: {a.out} written from the {a.version} write-up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
