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


def test_quiet_on_the_published_piece(tmp_path):
    # The first worked example must pass its own gate.
    piece = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "content",
                         "2026-08-15-plumb-line-0.9.0-the-front-door.md")
    assert ccl.check(piece) == []


def test_quiet_on_plain_prose(tmp_path):
    flags = _flags_for(tmp_path, "The Node floor rose from 16 to 20. CI tests it.\n")
    assert flags == []


def test_strict_exit_codes(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("A battle-tested toolkit.\n", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text("A toolkit with recorded validation results.\n", encoding="utf-8")
    assert ccl.main(["ccl", str(bad), "--strict"]) == 1
    assert ccl.main(["ccl", str(bad)]) == 0          # flagger, not a gate
    assert ccl.main(["ccl", str(good), "--strict"]) == 0
