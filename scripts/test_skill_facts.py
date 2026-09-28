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
    # `===` compares array identity: a test written from this never passes.
    assert not re.search(r"===\s*\[\s*\]|\.toBe\(\s*\[\s*\]\s*\)", SKILLS[skill]), skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_confidence_is_never_written_as_a_number(skill):
    # confidence is a rung (none|low|medium|high); the number is confidenceScore.
    # JS `confidence: 0`, Python `confidence=0`, dict/JSON `'confidence': 0`.
    assert not re.search(r"\bconfidence['\"]?\s*[:=]\s*[0-9]", SKILLS[skill]), skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_skills_do_not_call_the_shipped_checker_unavailable(skill):
    for phrase in ("common case in a consumer repo", "usually unavailable", "is not reachable (the"):
        assert phrase not in SKILLS[skill], (skill, phrase)
    if "check_report_format.py" in SKILLS[skill]:
        assert "<plugin root>/scripts/check_report_format.py" in SKILLS[skill], (
            f"{skill} names the checker but not where it ships in the plugin")


# #514: an agent copies a skill's own wording into its report or record, and
# the report contract rejects a principle code that is not inline-named with
# its canonical name. So the skills whose output the checker validates must
# model that form. As strict as the checker on names (the canonical name must
# follow the dash), and stricter on joiners on purpose: a code joined by "/"
# or "-" (P1/P2, P6-adjacent) is still a bare citation to a reader, whatever
# the checker's path-shaped exclusions let through. Inline code spans are
# masked, as the checker masks them: that is where a skill quotes the forms
# it forbids. A range (P1–P9) is not a citation.
_SKILL_CODE = re.compile(r"(?<![\w–—])P([1-9])(?![\w–—])")
_FENCE_LINE = re.compile(r"^[ \t]*(?:```+|~~~+).*$", re.M)
# A span may soft-wrap onto the next line, so it may cross a newline, but not
# a blank line: one stray backtick must not mask the rest of the file.
_CODE_SPAN = re.compile(r"`(?:[^`\n]|\n(?![ \t]*\n))*`")
_PRINCIPLE_HEADING = re.compile(r"^## Principle (\d) — (.+?)\s*$", re.M)
PRINCIPLES = dict(_PRINCIPLE_HEADING.findall(_read(_ROOT, "reference", "portable-principles.md")))


def _scan_codes(text):
    """(bare, named): lines citing a code without its canonical name, and the
    set of codes seen correctly inline-named, after masking."""
    masked = _FENCE_LINE.sub(lambda m: " " * len(m.group(0)), text)
    masked = _CODE_SPAN.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), masked)
    lines, masked_lines = text.split("\n"), masked.split("\n")
    assert len(lines) == len(masked_lines), "masking must keep line numbers"
    bare, named = [], set()
    for n, line in enumerate(masked_lines, 1):
        for m in _SKILL_CODE.finditer(line):
            # The name may start on the next line when the prose wraps after "—".
            rest = line[m.end():] + " " + (masked_lines[n].lstrip() if n < len(masked_lines) else "")
            dash = re.match(r"[ \t]*—[ \t]*", rest)
            if dash and rest[dash.end():].startswith(PRINCIPLES[m.group(1)]):
                named.add(m.group(1))
                continue
            bare.append(f"line {n}: {lines[n - 1].strip()[:90]}")
            break
    return bare, named


def _bare_codes(text):
    return _scan_codes(text)[0]


def test_principle_names_are_read_from_the_reference():
    assert sorted(PRINCIPLES) == [str(i) for i in range(1, 10)], PRINCIPLES


# The skills whose output check_report_format.py validates for principle
# names (audit reports, remediation records), plus adopt, whose routing
# output names principles in prose an agent may carry forward.
@pytest.mark.parametrize("skill", ["plumb-line-audit", "plumb-line-remediate", "plumb-line-adopt"])
def test_skill_models_inline_named_codes(skill):
    bare, _ = _scan_codes(SKILLS[skill])
    assert bare == [], f"principle codes not inline-named in {skill}:\n" + "\n".join(bare)


def test_the_scan_sees_the_audit_skills_named_codes():
    # Guards a vacuous pass: if masking ever blanked the file, the scan would
    # find no bare codes and also no named ones. The audit skill's glossary
    # example names all nine.
    _, named = _scan_codes(SKILLS["plumb-line-audit"])
    assert named == set(PRINCIPLES), sorted(set(PRINCIPLES) - named)


def test_bare_code_scan_catches_the_forms_it_must():
    assert _bare_codes("the audit's P1/P2 coverage is partial")
    assert _bare_codes("a P6-adjacent advisory")
    assert _bare_codes("this violates P3.")
    assert _bare_codes("a **P3** finding")
    assert _bare_codes("| x | P8 |")
    assert _bare_codes("P3 — Confidence and provenance")           # wrong name
    assert _bare_codes("P9 — the explanation IS the fix")          # wrong name
    assert _bare_codes("a `stray tick\n\nthen P3 in the next paragraph")
    assert not _bare_codes("P3 — Confidence + provenance")
    assert not _bare_codes("P1–P9")
    assert not _bare_codes("never `Provenance (P3)`")
    assert not _bare_codes("a header (`Provenance (P3 —\nConfidence + provenance)`, not `Provenance (P3)`)")
    assert not _bare_codes("cite P3 —\nConfidence + provenance")
    assert _bare_codes("```\na fenced example citing P3 bare\n```")   # examples get copied too
