"""Facts the skills state about the code, pinned so they cannot drift (#445).

The skills ship in the plugin and are followed literally by agents. The
2026-09-25 staleness sweep found them teaching things the code contradicts:
a vendoring list that omitted a bundled file (a vendored copy then lost the
baseline API), a numeric `confidence: 0` the envelope does not accept, a JS
`=== []` assertion that can never pass, and "the checker is usually
unavailable" when it ships inside the plugin.

Run from the repo root: python3 -m pytest -q scripts/test_skill_facts.py
"""
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKILLS = os.path.join(_ROOT, "skills")
_BUNDLE = os.path.join(_ROOT, ".claude-plugin", "bundled", "primitives")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


SKILLS = {d: _read(_SKILLS, d, "SKILL.md") for d in sorted(os.listdir(_SKILLS))
          if os.path.isfile(os.path.join(_SKILLS, d, "SKILL.md"))}


@pytest.mark.parametrize("lang", ["js", "python"])
def test_bootstrap_vendoring_list_is_the_whole_bundle(lang):
    bundled = {f for f in os.listdir(os.path.join(_BUNDLE, lang))
               if f.endswith((".mjs", ".py"))}
    text = SKILLS["plumb-line-bootstrap"]
    section = text[text.index("bundled/primitives/js/"):text.index("They carry a dual-import shim")]
    ext = ".mjs" if lang == "js" else ".py"
    listed = set(re.findall(r"`([\w]+%s)`" % re.escape(ext), section))
    assert listed == bundled, f"bootstrap lists {sorted(listed)}; the {lang} bundle has {sorted(bundled)}"


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_no_js_array_identity_assertion(skill):
    # `[] === []` is always false: a test written from this never passes.
    assert "=== []" not in SKILLS[skill], skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_confidence_is_never_written_as_a_number(skill):
    # confidence is a rung (none|low|medium|high); the number is confidenceScore.
    assert not re.search(r"\bconfidence:\s*[0-9]", SKILLS[skill]), skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_skills_do_not_call_the_shipped_checker_unavailable(skill):
    assert "common case in a consumer repo" not in SKILLS[skill], skill
    if "check_report_format.py" in SKILLS[skill]:
        assert "<plugin root>/scripts/check_report_format.py" in SKILLS[skill], (
            f"{skill} names the checker but not where it ships in the plugin")
