"""Tests for scripts/check_content_language.py — the content-language flagger
(gate 2 of the release-to-content routine, GH #255).

Run from the repo root:

    python3 -m pytest -q scripts/test_content_language.py

Mirrors the scripts/test_version_prose.py precedent: loaded by path under a
private module name.
"""
import importlib.util
import os

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "check_content_language.py")
_spec = importlib.util.spec_from_file_location("_check_content_language", _SCRIPT)
ccl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccl)


def _flags_for(tmp_path, text):
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return ccl.check(str(p))


def test_flags_the_banned_patterns(tmp_path):
    text = (
        "This is not a linter, it's a revolution.\n"
        "We delve into the agent landscape to unlock value.\n"
        "A blazingly fast, battle-tested, production-ready core.\n"
        "The floor rose, and it matters.\n"
    )
    flags = _flags_for(tmp_path, text)
    labels = {label for _, label, _ in flags}
    assert "not-X-but-Y construction" in labels
    assert "register: delve" in labels
    assert "register: landscape (figurative)" in labels
    assert "register: unlock (figurative)" in labels
    assert "hollow superlative" in labels
    assert "unverifiable maturity claim" in labels
    assert "roll-on emphasis tail" in labels


_CONTENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "docs", "content")


def test_published_0_9_0_piece_carries_exactly_its_one_recorded_keep():
    # The first worked example is pinned as a dated artifact, not as
    # flag-free: "verified by import, / not by execution" (lines 17-18) is a
    # bare contrast split across a hard wrap. It predates the 2026-08-18
    # bare-contrast ruling and is kept on purpose (#316). Until the flagger
    # unwrapped paragraphs this test pinned the piece flag-free, enshrining
    # the miss; now it pins the miss as a conscious keep, so a second flag
    # appearing in the piece still fails here.
    flags = ccl.check(os.path.join(_CONTENT, "2026-08-15-plumb-line-0.9.0-the-front-door.md"))
    assert [(ln, label) for ln, label, _ in flags] == \
        [(17, "bare contrast (X, not Y / not X but Y)")], flags


def test_published_0_10_0_piece_is_flag_free():
    # Written after the ruling; must stay clean under the unwrapped scan.
    assert ccl.check(os.path.join(_CONTENT, "2026-08-19-plumb-line-0.10.0-pay-down-the-ledger.md")) == []


def test_banned_construction_split_across_a_wrap_is_flagged(tmp_path):
    # #316: per-physical-line matching let a hard wrap hide a construction.
    text = (
        "Three snippets crashed; they had been verified by import,\n"
        "not by execution. A test now runs each one.\n"
        "\n"
        "This is not\n"
        "a linter, it is a discipline.\n"
    )
    flags = _flags_for(tmp_path, text)
    assert [(ln, label) for ln, label, _ in flags] == [
        (1, "bare contrast (X, not Y / not X but Y)"),
        (4, "not-X-but-Y construction"),
    ], flags


def test_wrapped_flag_reports_both_physical_lines(tmp_path):
    text = "verified by import,\nnot by execution.\n"
    (_ln, _label, shown), = _flags_for(tmp_path, text)
    assert "verified by import," in shown and "not by execution." in shown


def test_paragraph_break_is_not_a_wrap(tmp_path):
    # A blank line ends the paragraph: "X, [blank] not Y" is two sentences
    # in two paragraphs, not one construction.
    flags = _flags_for(tmp_path, "The contract is a data file,\n\nnot prose.\n")
    assert flags == []


def test_quiet_on_plain_prose(tmp_path):
    flags = _flags_for(tmp_path, "The Node floor rose from 16 to 20. CI tests it.\n")
    assert flags == []


def test_h2_ascii_header_is_not_an_emoji_header(tmp_path):
    # GH #286: `#{1,6}` backtracked so the second '#' satisfied the negated
    # class, flagging every h2-or-deeper ASCII header as an emoji header.
    flags = _flags_for(tmp_path, "## The one property\n### Deeper still\n")
    assert flags == []


def test_actual_emoji_header_still_flags(tmp_path):
    flags = _flags_for(tmp_path, "## 🎯 Goals\n")
    assert [label for _, label, _ in flags] == ["emoji header"]


def test_flags_quiet_part(tmp_path):
    # Barred 2026-08-18 after appearing in a design-note draft.
    flags = _flags_for(tmp_path, "Its own header says the quiet part.\n")
    assert "register: quiet part" in {label for _, label, _ in flags}


def test_flags_bare_contrast_constructions(tmp_path):
    # The existing pattern only caught "it is not X, it is Y"; drafts leaned
    # on the bare forms instead. Barred 2026-08-18.
    text = (
        "The contract is a data file, not prose.\n"
        "Parity is enforced not by prose but by data.\n"
    )
    flags = _flags_for(tmp_path, text)
    labels = [label for _, label, _ in flags]
    assert labels.count("bare contrast (X, not Y / not X but Y)") == 2


def test_em_dashes_counted_but_not_flagged(tmp_path):
    # Em dashes are reported as an informational count (keep to a bare
    # minimum), never as flags. (The published 0.9.0 piece uses one; its own
    # pin is the one-recorded-keep test above, not flag-free.)
    p = tmp_path / "draft.md"
    p.write_text("One thing — and another — again.\n", encoding="utf-8")
    assert ccl.check(str(p)) == []
    assert ccl.em_dashes(str(p)) == 2


def test_strict_exit_codes(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("A battle-tested toolkit.\n", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text("A toolkit with recorded validation results.\n", encoding="utf-8")
    assert ccl.main(["ccl", str(bad), "--strict"]) == 1
    assert ccl.main(["ccl", str(bad)]) == 0          # flagger, not a gate
    assert ccl.main(["ccl", str(good), "--strict"]) == 0


# --- length follows the release (owner decision 2026-09-25) -----------------
# The patch write-ups had grown longer than the minors (0.11.1 and 0.11.2 at
# ~810-830 words against 0.11.0's 582). Density follows the version: a patch
# gets a short piece. Budgets count the body above the disclosure rule.

import glob  # noqa: E402
import re  # noqa: E402

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "docs", "content")
_PIECE = re.compile(r"^\d{4}-\d{2}-\d{2}-plumb-line-(\d+)\.(\d+)\.(\d+)-.+\.md$")
WORD_BUDGET = {"patch": 300, "minor": 600, "major": 1000}
# Written before the budget existed; kept as dated artifacts, not rewritten.
GRANDFATHERED = {
    "2026-08-15-plumb-line-0.9.0-the-front-door.md",
    "2026-08-19-plumb-line-0.10.0-pay-down-the-ledger.md",
    "2026-09-15-plumb-line-0.11.0-honest-over-time.md",
    "2026-09-20-plumb-line-0.11.1-measured-nothing.md",
    "2026-09-25-plumb-line-0.11.2-the-checkers-own-blind-spot.md",
}


def release_kind(major, minor, patch):
    """Pre-1.0, a minor is the feature/breaking release (the project's SemVer
    rule); from 1.0 a major is. A patch is always a patch."""
    if patch:
        return "patch"
    if major >= 1 and minor == 0:
        return "major"
    return "minor"


def body_words(text):
    return len(text.split("\n---\n")[0].split())


def test_release_kind_follows_semver():
    assert release_kind(0, 11, 3) == "patch"
    assert release_kind(0, 12, 0) == "minor"
    assert release_kind(1, 0, 0) == "major"
    assert release_kind(1, 2, 0) == "minor"


def test_the_budget_would_have_caught_the_long_patches():
    path = os.path.join(_CONTENT_DIR, "2026-09-25-plumb-line-0.11.2-the-checkers-own-blind-spot.md")
    with open(path, encoding="utf-8") as fh:
        assert body_words(fh.read()) > WORD_BUDGET["patch"]


def test_every_new_piece_fits_its_release_budget():
    pieces = [p for p in glob.glob(os.path.join(_CONTENT_DIR, "*.md"))
              if _PIECE.match(os.path.basename(p))]
    assert pieces, "no release pieces found"
    for path in pieces:
        name = os.path.basename(path)
        if name in GRANDFATHERED:
            continue
        kind = release_kind(*(int(g) for g in _PIECE.match(name).groups()))
        with open(path, encoding="utf-8") as fh:
            words = body_words(fh.read())
        assert words <= WORD_BUDGET[kind], (
            f"{name} is a {kind} piece at {words} words; the budget is "
            f"{WORD_BUDGET[kind]} (docs/content/TEMPLATE.md, 'Length follows the release')")
