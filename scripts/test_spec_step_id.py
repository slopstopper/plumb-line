"""SPEC §4's step-id canonical form, checked against both implementations (#401).

A third-language port is written from SPEC.md, so the spec's description of
the canonical form must be the one the implementations hash. The spec carries
a worked example (a step, its canonical bytes, its id); this suite checks the
bytes hash to the stated id and that JS and Python produce that id for the
step. The example's score (0.00001) is one where JSON number formatting
differs across languages, so a spec that said "JSON number" would fail here.

Run from the repo root: python3 -m pytest -q scripts/test_spec_step_id.py
"""
import hashlib
import json
import os
import re
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = os.path.join(_ROOT, 'primitives', 'SPEC.md')

with open(_SPEC, encoding='utf-8') as fh:
    SPEC = fh.read()

_EXAMPLE = re.search(
    r'<!-- step-id worked example: (?P<step>\{.*?\}) -->\s*```text\n(?P<canon>.*?)\n```\s*'
    r'hashes to `(?P<id>sha256:[0-9a-f]{12})`',
    SPEC, re.DOTALL)


def _example():
    assert _EXAMPLE, 'SPEC.md has no step-id worked example in the expected shape'
    return json.loads(_EXAMPLE['step']), _EXAMPLE['canon'], _EXAMPLE['id']


def test_template_names_the_ieee754_hex_encoding():
    line = next(ln for ln in SPEC.splitlines() if ln.startswith('confidenceScore=<'))
    assert 'IEEE-754' in line and 'hex' in line, line


def test_worked_example_bytes_hash_to_the_stated_id():
    _, canon, sid = _example()
    assert 'sha256:' + hashlib.sha256(canon.encode('utf-8')).hexdigest()[:12] == sid


def test_python_implementation_produces_the_stated_id():
    step, _, sid = _example()
    script = ('import json, sys; sys.path.insert(0, "primitives/python"); import provenance as p; '
              's = json.loads(sys.argv[1]); '
              'print(p.step_id({"of": s["of"], "source": s["source"], "confidence": s["confidence"], '
              '"derived_from_mock": s["derivedFromMock"], "confidence_score": s["confidenceScore"]}))')
    # A subprocess, so primitives/python never lands on this process's sys.path
    # (its http.py shadows the stdlib http package, #171).
    out = subprocess.run(['python3', '-c', script, json.dumps(step)], cwd=_ROOT,
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == sid


def test_js_implementation_produces_the_stated_id():
    step, _, sid = _example()
    script = ('import { stepId } from "./primitives/js/provenance.mjs";'
              'console.log(stepId(JSON.parse(process.argv[1]), []));')
    out = subprocess.run(['node', '--input-type=module', '-e', script, json.dumps(step)],
                         cwd=_ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == sid
