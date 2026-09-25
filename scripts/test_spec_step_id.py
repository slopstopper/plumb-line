"""SPEC §4's step-id canonical form, checked against both implementations (#401).

A third-language port is written from SPEC.md, so the spec's description of
the canonical form must be the one the implementations hash. The spec carries
worked examples (a step, its canonical bytes, its id); this suite checks the
bytes hash to the stated id and that JS and Python produce that id for the
step. The first example's score (0.00001) is one where JSON number formatting
differs across languages, so a spec that said "JSON number" would fail here.
The second gives two input ids UNSORTED and no score, so the sort, join and
"-" rules are exercised too.

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

_EXAMPLES = list(re.finditer(
    r'<!-- step-id worked example: (?P<step>\{.*?\}) -->\s*```text\n(?P<canon>.*?)\n```\s*'
    r'hashes to `(?P<id>sha256:[0-9a-f]{12})`',
    SPEC, re.DOTALL))


def _examples():
    """(step, input_ids, canonical text, id) per worked example. A step's
    `inputIds` are the ids passed to stepId/step_id, as the spec gives them."""
    assert len(_EXAMPLES) >= 2, 'SPEC.md needs both step-id worked examples (score; unsorted inputs)'
    out = []
    for m in _EXAMPLES:
        step = json.loads(m['step'])
        out.append((step, step.pop('inputIds', []), m['canon'], m['id']))
    return out


def test_template_names_the_ieee754_hex_encoding():
    line = next(ln for ln in SPEC.splitlines() if ln.startswith('confidenceScore=<'))
    assert 'IEEE-754' in line and 'hex' in line, line


def test_worked_example_bytes_hash_to_the_stated_id():
    for _, _, canon, sid in _examples():
        assert 'sha256:' + hashlib.sha256(canon.encode('utf-8')).hexdigest()[:12] == sid


def test_python_implementation_produces_the_stated_id():
    script = ('import json, sys; sys.path.insert(0, "primitives/python"); import provenance as p; '
              's, ids = json.loads(sys.argv[1]), json.loads(sys.argv[2]); '
              'print(p.step_id({"of": s["of"], "source": s["source"], "confidence": s["confidence"], '
              '"derived_from_mock": s["derivedFromMock"], "confidence_score": s.get("confidenceScore")}, ids))')
    for step, ids, _, sid in _examples():
        # A subprocess, so primitives/python never lands on this process's
        # sys.path, where its flat module names could shadow a sibling suite's.
        out = subprocess.run(['python3', '-c', script, json.dumps(step), json.dumps(ids)], cwd=_ROOT,
                             capture_output=True, text=True, check=True)
        assert out.stdout.strip() == sid


def test_js_implementation_produces_the_stated_id():
    script = ('import { stepId } from "./primitives/js/provenance.mjs";'
              'console.log(stepId(JSON.parse(process.argv[1]), JSON.parse(process.argv[2])));')
    for step, ids, _, sid in _examples():
        out = subprocess.run(['node', '--input-type=module', '-e', script, json.dumps(step), json.dumps(ids)],
                             cwd=_ROOT, capture_output=True, text=True, check=True)
        assert out.stdout.strip() == sid
