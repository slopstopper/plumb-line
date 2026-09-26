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


def test_titled_and_reference_style_links_become_absolute_too():
    text = '[t](../../CHANGELOG.md "the log")\n\n[ref]: ../dogfood.md\n'
    out = rn.absolute_links(text, REPO, "v9.9.9", "docs/content/x.md")
    assert f'[t]({URL}/CHANGELOG.md "the log")' in out
    assert f"[ref]: {URL}/docs/dogfood.md" in out


def test_a_link_that_escapes_the_repository_is_an_error():
    with pytest.raises(SystemExit, match="escapes the repository"):
        rn.absolute_links("[x](../../../outside.md)", REPO, "v9.9.9", "docs/content/x.md")


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


# --- The workflow's own shell, run for real (#480 review): the two release
# steps' `run:` blocks from release.yml, under bash -e as Actions runs them,
# with a stub `gh` that logs its calls and plays the release's state, and the
# real release_notes.py. v0.11.4 has a shipped write-up; v9.9.9 has none.

WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"

STUB_GH = r"""#!/bin/bash
echo "gh $*" >> "$GH_LOG"
case "$1 $2" in
  "release view")
    if [ "$4" = "--json" ]; then printf '%s\n' "$STUB_BODY"; exit 0; fi
    [ "$STUB_EXISTS" = 1 ] ;;
  "release create"|"release edit")
    while [ $# -gt 0 ]; do
      if [ "$1" = "--notes-file" ]; then cp "$2" "$GH_LOG.notes"; fi
      shift
    done ;;
  "issue list") echo 0 ;;
esac
"""


def _run_block(step_name):
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text[text.index(f"- name: {step_name}"):]
    step = step[:step.find("\n      - ", 1)] if "\n      - " in step[1:] else step
    lines = []
    for line in step[step.index("run: |\n") + len("run: |\n"):].splitlines():
        if line.strip() and not line.startswith(" " * 10):
            break  # the block ends at the first line indented less than it
        lines.append(line[10:])
    return "\n".join(lines)


def _run_release_steps(tmp_path, tag, exists=False, body=""):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(STUB_GH)
    gh.chmod(0o755)
    (bin_dir / "python").symlink_to(sys.executable)
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    log = tmp_path / "gh.log"
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "GH_LOG": str(log), "RUNNER_TEMP": str(runner_temp),
           "GITHUB_REF_NAME": tag, "GITHUB_REPOSITORY": REPO, "STUB_EXISTS": "1" if exists else "0",
           "STUB_BODY": body}
    for step in ("Create GitHub release", "Open the content-draft-due issue"):
        r = subprocess.run(["bash", "-e", "-c", _run_block(step)], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        assert r.returncode == 0, (step, r.stdout, r.stderr)
    calls = log.read_text().splitlines() if log.exists() else []
    notes = Path(f"{log}.notes").read_text() if Path(f"{log}.notes").exists() else None
    return calls, notes


def test_new_release_with_a_write_up_gets_it_above_the_generated_notes(tmp_path):
    calls, notes = _run_release_steps(tmp_path, "v0.11.4")
    create = [c for c in calls if c.startswith("gh release create")]
    assert len(create) == 1 and "--generate-notes" in create[0] and "--notes-file" in create[0], calls
    assert notes.startswith("# plumb-line 0.11.4") and "Canonical copy:" in notes
    assert not any(c.startswith("gh issue create") for c in calls), "no draft is due when the piece shipped"


def test_new_release_without_a_write_up_gets_generated_notes_and_a_draft_due_issue(tmp_path):
    calls, notes = _run_release_steps(tmp_path, "v9.9.9")
    create = [c for c in calls if c.startswith("gh release create")]
    assert len(create) == 1 and "--notes-file" not in create[0], calls
    assert notes is None
    assert any(c.startswith("gh issue create") for c in calls), calls


def test_existing_release_gets_the_write_up_on_top_of_its_body(tmp_path):
    calls, notes = _run_release_steps(tmp_path, "v0.11.4", exists=True, body="## What's Changed\n* a PR")
    assert any(c.startswith("gh release edit v0.11.4") for c in calls), calls
    assert notes.startswith("# plumb-line 0.11.4")
    assert notes.index("Canonical copy:") < notes.index("## What's Changed"), "old body kept, below"
    assert not any(c.startswith("gh release create") for c in calls)


def test_existing_release_that_already_carries_the_write_up_is_left_alone(tmp_path):
    calls, _ = _run_release_steps(tmp_path, "v0.11.4", exists=True,
                                  body="# plumb-line 0.11.4\n*Canonical copy: [x](y).*\n## What's Changed")
    assert not any(c.startswith(("gh release edit", "gh release create")) for c in calls), calls
