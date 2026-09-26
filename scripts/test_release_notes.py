"""Tests for scripts/release_notes.py (#480): the approved write-up goes into
the published GitHub release, with links that work on the release page."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_notes as rn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPO = "slopstopper/plumb-line"
URL = f"https://github.com/{REPO}/blob/v9.9.9"


def _content(tmp_path, name, text):
    d = tmp_path / "docs" / "content"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_finds_the_write_up_for_the_version(tmp_path):
    root = _content(tmp_path, "2026-01-01-plumb-line-9.9.9-a-title.md", "# t\n")
    _content(tmp_path, "2026-01-01-plumb-line-9.9.90-other.md", "# other\n")
    assert rn.find_write_up(root, "9.9.9").name == "2026-01-01-plumb-line-9.9.9-a-title.md"


def test_no_write_up_is_none(tmp_path):
    assert rn.find_write_up(_content(tmp_path, "TEMPLATE.md", "x"), "9.9.9") is None


def test_two_write_ups_for_one_version_is_an_error(tmp_path):
    root = _content(tmp_path, "2026-01-01-plumb-line-9.9.9-a.md", "a")
    _content(tmp_path, "2026-01-02-plumb-line-9.9.9-b.md", "b")
    with pytest.raises(SystemExit, match="more than one write-up"):
        rn.find_write_up(root, "9.9.9")


def test_relative_links_become_absolute_at_the_tag():
    text = ("[CHANGELOG](../../CHANGELOG.md), [results](../validation-results.md), "
            "[a section](../dogfood.md#v0114), [ext](https://example.com/x), "
            "[#1](https://github.com/slopstopper/plumb-line/issues/1), [anchor](#top)")
    out = rn.absolute_links(text, REPO, "v9.9.9", "docs/content/x.md")
    assert f"[CHANGELOG]({URL}/CHANGELOG.md)" in out
    assert f"[results]({URL}/docs/validation-results.md)" in out
    assert f"[a section]({URL}/docs/dogfood.md#v0114)" in out
    assert "[ext](https://example.com/x)" in out
    assert "[#1](https://github.com/slopstopper/plumb-line/issues/1)" in out
    assert "[anchor](#top)" in out


def test_notes_end_with_the_canonical_copy_and_a_rule(tmp_path):
    root = _content(tmp_path, "2026-01-01-plumb-line-9.9.9-a-title.md",
                    "# plumb-line 9.9.9\n\nBody with [log](../../CHANGELOG.md).\n")
    notes = rn.build_notes(root, "9.9.9", REPO, "v9.9.9")
    assert notes.startswith("# plumb-line 9.9.9\n")
    assert f"[log]({URL}/CHANGELOG.md)" in notes
    path = "docs/content/2026-01-01-plumb-line-9.9.9-a-title.md"
    assert f"*Canonical copy: [{path}]({URL}/{path}).*" in notes
    assert notes.rstrip().endswith("---")


def test_cli_writes_nothing_when_there_is_no_write_up(tmp_path):
    out = tmp_path / "notes.md"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "release_notes.py"), "9.9.9",
                        "--repo", REPO, "--ref", "v9.9.9", "--root", str(tmp_path), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert not out.exists()
    assert "no write-up" in r.stdout


def test_every_shipped_write_up_renders_with_no_relative_links_left():
    for piece in sorted((ROOT / "docs" / "content").glob("*-plumb-line-*.md")):
        version = re.search(r"-plumb-line-(\d+\.\d+\.\d+)-", piece.name).group(1)
        notes = rn.build_notes(ROOT, version, REPO, f"v{version}")
        leftover = [m for m in re.findall(r"\]\(([^)]+)\)", notes)
                    if not m.startswith(("http://", "https://", "#", "mailto:"))]
        assert not leftover, (piece.name, leftover)


def test_the_release_workflow_uses_the_script_and_skips_the_draft_issue_when_it_shipped():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "scripts/release_notes.py" in wf
    assert "--generate-notes" in wf and "--notes-file" in wf
    create = wf[wf.index("name: Create GitHub release"):wf.index("name: Open the content-draft-due issue")]
    assert "gh release edit" in create, "an existing release (the no-terminal route) must get the write-up too"
    draft = wf[wf.index("name: Open the content-draft-due issue"):]
    assert "notes.md" in draft.split("name:")[1], "the draft-due issue must be skipped when the write-up shipped"
