"""bump-version.mjs promotes the CHANGELOG's Unreleased notes verbatim.

The v0.11.5 bump spliced the whole file header into an entry: the notes went
into a String.replace replacement string, where `$`` means "the text before the
match". Run the real script on a scratch tree whose notes hold every special
replacement pattern, and require them back byte for byte.
"""
import json
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "bump-version.mjs"

NOTES = (
    "### Fixed\n"
    "- Python's `$` matched before a trailing newline; `$`` `$&` `$'` `$1` `$$` stay as written.\n"
    "- A second note with $&, $1 and $' outside backticks."
)


def _tree(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "bump-version.mjs")
    files = {
        "primitives/js/package.json": '{\n  "name": "x",\n  "version": "0.1.0"\n}\n',
        ".claude-plugin/plugin.json": '{\n  "name": "x",\n  "version": "0.1.0"\n}\n',
        "primitives/python/pyproject.toml": '[project]\nname = "x"\nversion = "0.1.0"\n',
        "docs/constraints.md": "- Release version is **0.1.0**, and so on.\n",
        "ACTION.md": "uses: slopstopper/plumb-line@v0.1.0\n",
        "primitives/js/package-lock.json": json.dumps(
            {"name": "x", "version": "0.1.0", "packages": {"": {"version": "0.1.0"}}}, indent=2) + "\n",
        "CHANGELOG.md": (
            "# Changelog\n\nHeader text that must stay in the header.\n\n"
            "## [Unreleased]\n\n" + NOTES + "\n\n"
            "## [0.1.0] — 2026-01-01\n\n- first\n\n"
            "[Unreleased]: https://github.com/o/r/compare/v0.1.0...HEAD\n"
            "[0.1.0]: https://github.com/o/r/releases/tag/v0.1.0\n"
        ),
    }
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def test_changelog_notes_are_promoted_verbatim(tmp_path):
    _tree(tmp_path)
    r = subprocess.run(["node", str(tmp_path / "scripts" / "bump-version.mjs"), "0.2.0"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    section = out.split("## [0.2.0] — ", 1)[1].split("\n", 1)[1]
    assert section.split("\n\n## [0.1.0]", 1)[0].strip() == NOTES
    assert out.count("Header text that must stay in the header.") == 1
    assert "## [Unreleased]\n\n_Nothing yet._\n\n## [0.2.0]" in out
    assert "[0.2.0]: https://github.com/o/r/compare/v0.1.0...v0.2.0" in out
