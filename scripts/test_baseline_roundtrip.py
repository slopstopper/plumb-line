"""JS writes a baseline, Python checks it (and vice versa). The file is the
contract; this proves both writers and both readers agree on real bytes.

Run from the repo root: python3 -m pytest -q scripts/test_baseline_roundtrip.py
"""
import json
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PY = os.path.join(_ROOT, 'primitives', 'python')
sys.path.insert(0, _PY)
import baseline as bl  # noqa: E402
from marked import mark, derive  # noqa: E402

_JS_WRITE = """
import { mark, derive } from "%s/primitives/js/marked.mjs";
import { update } from "%s/primitives/js/baseline.mjs";
const r = mark(0.04, { source: "real", confidence: "high", confidenceScore: 0.9 });
const f = mark(1.03, { source: "fallback", confidence: "medium", confidenceScore: 0.5 });
update("fx-rate", derive([r, f], (a, b) => a * b, { basis: "pricing.applyFx@v3" }),
       { because: "written by JS", dir: process.argv[2], date: "2026-09-10" });
"""

_JS_CHECK = """
import { mark, derive } from "%s/primitives/js/marked.mjs";
import { check } from "%s/primitives/js/baseline.mjs";
const r = mark(0.04, { source: "real", confidence: "high", confidenceScore: 0.9 });
const f = mark(1.03, { source: "fallback", confidence: "medium", confidenceScore: 0.5 });
const rep = check("fx-rate", derive([r, f], (a, b) => a * b, { basis: "pricing.applyFx@v3" }), { dir: process.argv[2] });
console.log(JSON.stringify({ status: rep.status, summary: rep.summary }));
"""


def _node(script, tmp_path, dir_):
    p = tmp_path / 'script.mjs'
    p.write_text(script % (_ROOT, _ROOT), encoding='utf-8')
    out = subprocess.run(['node', str(p), str(dir_)], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _py_marked():
    r = mark(0.04, source='real', confidence='high', confidence_score=0.9)
    f = mark(1.03, source='fallback', confidence='medium', confidence_score=0.5)
    return derive([r, f], lambda a, b: a * b, basis='pricing.applyFx@v3')


def test_js_writes_python_matches(tmp_path):
    d = tmp_path / 'b'
    _node(_JS_WRITE, tmp_path, d)
    rep = bl.check('fx-rate', _py_marked(), dir=str(d))
    assert rep['status'] == 'match', bl.report_text(rep)


def test_python_writes_js_matches(tmp_path):
    d = tmp_path / 'b'
    bl.update('fx-rate', _py_marked(), because='written by Python', dir=str(d), date='2026-09-10')
    assert json.loads(_node(_JS_CHECK, tmp_path, d)) == {'status': 'match', 'summary': 'none'}


def test_both_writers_produce_the_same_parsed_record(tmp_path):
    js, py = tmp_path / 'js', tmp_path / 'py'
    _node(_JS_WRITE, tmp_path, js)
    bl.update('fx-rate', _py_marked(), because='written by JS', dir=str(py), date='2026-09-10')
    a = json.load(open(js / 'fx-rate.json', encoding='utf-8'))
    b = json.load(open(py / 'fx-rate.json', encoding='utf-8'))
    assert a == b
