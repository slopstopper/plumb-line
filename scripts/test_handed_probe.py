"""The handed-envelope differential probe (#525, #594).

primitives/conformance/handed_probe.py feeds the same handed inputs to
`combine`, the audit and the egress guard in both twins and counts where they
differ. PARITY.md cites its counts; this suite proves the probe runs, that its
classifier sorts a difference the way its docstring says, and that the counts
PARITY.md states are the ones the probe prints, so they are run, not typed.

Run from the repo root: python3 -m pytest -q scripts/test_handed_probe.py
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROBE = os.path.join(_ROOT, 'primitives', 'conformance', 'handed_probe.py')
_PARITY = os.path.join(_ROOT, 'primitives', 'PARITY.md')


def _load_probe():
    # Loaded by path. Importing it must not import the primitive: its flat
    # module names (provenance, audit, guard) would shadow a sibling suite's
    # (see test_bundle_conformance.py), so the probe imports them only when run.
    spec = importlib.util.spec_from_file_location('handed_probe', _PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_importing_the_probe_does_not_import_the_primitive():
    before = set(sys.modules)
    _load_probe()
    assert not {'provenance', 'audit', 'guard'} & (set(sys.modules) - before)


# --- the classifier ------------------------------------------------------

def test_equal_records_have_no_difference():
    probe = _load_probe()
    rec = {'combine': {'derivedFromMock': True, 'lineage': [{'id': 'sha256:abc'}]}, 'audit': [], 'guard': {'pass': True}}
    assert probe.diff(rec, json.loads(json.dumps(rec))) == []
    assert probe.classify([]) == 'agree'


def test_a_snake_case_field_name_in_a_message_is_a_name_difference():
    probe = _load_probe()
    d = probe.diff({'audit': ['x: derived_from_mock is not a boolean']},
                   {'audit': ['x: derivedFromMock is not a boolean']})
    assert [c for _, c in d] == ['field-name']
    assert probe.classify(d) == 'field-name'


# A number JSON cannot write (a non-finite one, or -0) reaches the comparison
# tagged, from both halves, so JSON.stringify's null and 0 hide nothing.
NEG0 = {'$number': '-0'}
INF = {'$number': 'Infinity'}


def test_python_tags_the_numbers_json_cannot_write():
    probe = _load_probe()
    assert probe.tag_numbers([-0.0, float('inf'), float('-inf'), 0.0, 0, 1.0, 10 ** 400]) == \
        [NEG0, INF, {'$number': '-Infinity'}, 0.0, 0, 1.0, 10 ** 400]
    assert probe.tag_numbers({'a': [float('nan')]}) == {'a': [{'$number': 'NaN'}]}


def test_the_same_value_tagged_in_both_halves_is_no_difference():
    probe = _load_probe()
    assert probe.diff({'combine': {'confidenceScore': NEG0}}, {'combine': {'confidenceScore': NEG0}}) == []
    assert probe.diff({'combine': {'source': INF}}, {'combine': {'source': INF}}) == []


@pytest.mark.parametrize('py, js', [
    (1.0, 1),             # Python's parser keeps a float; JS has one number type
    (0, NEG0),            # JSON's -0: Python's parser reads the integer 0, JS's reads -0
    (NEG0, 0),            # a -0.0 one twin holds and the other does not
    (10 ** 400, INF),     # beyond double range: Python's parser keeps the integer, JS's reads Infinity
])
def test_the_same_double_held_differently_is_a_number_difference(py, js):
    probe = _load_probe()
    d = probe.diff({'combine': {'lineage': [{'source': py}]}}, {'combine': {'lineage': [{'source': js}]}})
    assert [c for _, c in d] == ['number']
    assert probe.classify(d) == 'number'


def test_a_record_s_top_level_detail_is_not_compared_but_a_step_s_is():
    probe = _load_probe()
    assert probe.diff({'combine': {}, 'detail': 'KeyError'}, {'combine': {}, 'detail': 'TypeError'}) == []
    d = probe.diff({'combine': {'lineage': [{'detail': 'a'}]}}, {'combine': {'lineage': [{'detail': 'b'}]}})
    assert probe.classify(d) == 'outcome'


@pytest.mark.parametrize('py, js', [
    ('invalid envelope: lineage step 0 source -0.0 is not on the source ladder',
     'invalid envelope: lineage step 0 source 0 is not on the source ladder'),
    ('invalid envelope: lineage step 0 confidence 1e-07 is not on the confidence ladder',
     'invalid envelope: lineage step 0 confidence 1e-7 is not on the confidence ladder'),
    ('invalid envelope: lineage step 0 source {"a": 1} is not on the source ladder',
     'invalid envelope: lineage step 0 source {"a":1} is not on the source ladder'),
    ('invalid envelope: lineage step 0 source 1' + '0' * 400 + ' is not on the source ladder',
     'invalid envelope: lineage step 0 source Infinity is not on the source ladder'),
])
def test_one_value_quoted_in_each_language_s_rendering_is_a_quoted_value_difference(py, js):
    # As PARITY.md records for construct's refusals: the message is the same
    # apart from the value it quotes, which each language writes its own way.
    probe = _load_probe()
    d = probe.diff({'guard': {'refused': [py]}}, {'guard': {'refused': [js]}})
    assert [c for _, c in d] == ['quoted-value']


@pytest.mark.parametrize('py, js', [
    ('invalid envelope: lineage step 0 source 1 is not on the source ladder',
     'invalid envelope: lineage step 0 source 2 is not on the source ladder'),          # another value
    ('invalid envelope: lineage step 0 source 1 is not on the source ladder',
     'invalid envelope: lineage step 0 confidence 1 is not on the confidence ladder'),  # another field
    ('invalid envelope: lineage step 0 source [1] is not on the source ladder',
     'invalid envelope: lineage step 0 source {"0":1} is not on the source ladder'),    # another type
])
def test_a_message_quoting_a_different_value_is_an_outcome_difference(py, js):
    probe = _load_probe()
    d = probe.diff({'guard': {'refused': [py]}}, {'guard': {'refused': [js]}})
    assert probe.classify(d) == 'outcome'


@pytest.mark.parametrize('py, js', [
    ({'combine': {'derivedFromMock': True}}, {'combine': {'derivedFromMock': False}}),     # taint
    ({'combine': {'derivedFromMock': True}}, {'combine': {'derivedFromMock': 1}}),         # bool is not 1
    ({'guard': {'pass': True}}, {'guard': {'refused': ['mock: x']}}),                      # verdict
    ({'combine': {'lineage': [{'id': 'sha256:a'}]}}, {'combine': {'lineage': [{'id': 'sha256:b'}]}}),  # id
    ({'combine': {'lineage': [1, 2]}}, {'combine': {'lineage': [1]}}),                     # shape
    ({'combine': {'raises': True}}, {'combine': {'source': 'derived'}}),                   # one raises
    ({'audit': ['over-claiming: 1']}, {'audit': ['over-claiming: 2']}),                    # message text
    ({'combine': {'confidence': 0}}, {'combine': {'confidence': None}}),                   # a finite number is not null
    ({'combine': {'confidence': 10 ** 400}}, {'combine': {'confidence': None}}),          # nor is a huge one
    ({'combine': {'confidence': INF}}, {'combine': {'confidence': None}}),                # nor an infinite one
])
def test_any_other_difference_is_an_outcome_difference(py, js):
    probe = _load_probe()
    d = probe.diff(py, js)
    assert d and probe.classify(d) == 'outcome'


def test_a_name_and_a_number_difference_together_stay_below_outcome():
    probe = _load_probe()
    d = probe.diff({'audit': ['derived_from_mock'], 'combine': {'confidence': 1.0}},
                   {'audit': ['derivedFromMock'], 'combine': {'confidence': 1}})
    assert probe.classify(d) == 'field-name+number'


def test_the_corpus_is_json_text_each_language_parses_itself():
    # The parser difference is the point: -0.0 and an integer beyond double
    # range must reach each twin as text, not as a value one language made.
    corpus = _load_probe().corpus()
    texts = [text for _, text in corpus]
    assert len(set(texts)) == len(texts), 'duplicate probe inputs'
    assert all(isinstance(json.loads(t), list) for t in texts)
    assert any('-0.0' in t for t in texts) and any('1' + '0' * 400 in t for t in texts)
    names = [name for name, _ in corpus]
    assert len(set(names)) == len(names), 'duplicate probe input names'


# --- the probe, run --------------------------------------------------------

def _run_probe(*args):
    if shutil.which('node') is None:
        pytest.skip('node is not on PATH; the probe runs the JS twin')
    proc = subprocess.run([sys.executable, _PROBE, '--json', *args], cwd=_ROOT,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode in (0, 1), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_the_probe_runs_both_twins_and_finds_no_outcome_difference():
    code, out = _run_probe()
    assert out['inputs'] == len(_load_probe().corpus()) > 0
    assert out['inputs'] == out['agree'] + out['differ']
    assert out['differ'] == sum(n for cls, n in out['byClass'].items())
    assert out['byClass'].get('outcome', 0) == 0, out['differences']
    assert code == 0


# The parent of #525's first fix 8cef0a2, in full so it cannot grow ambiguous:
# the tree the divergences were found in.
_PRE_525 = '2e6ebc56f9294323e864842dc7f2f4eab836060e'


def _stated_counts(column):
    """One column of PARITY.md's probe table, as {class: inputs}: the rows
    between the handed-probe markers, each `| `class` | main | before |`.
    A class the probe does not print is stated as 0, so `outcome` can be shown."""
    with open(_PARITY, encoding='utf-8') as fh:
        parity = fh.read()
    m = re.search(r'<!-- handed-probe counts -->(.*?)<!-- /handed-probe counts -->', parity, re.DOTALL)
    assert m, 'PARITY.md has no handed-probe counts table between its markers'
    rows = re.findall(r'^\| `([a-z+-]+)` +\| +(\d+) +\| +(\d+) +\|', m.group(1), re.MULTILINE)
    assert rows, 'the handed-probe counts table has no rows this test can read'
    return {cls: int(counts[column]) for cls, *counts in rows if int(counts[column])}


def _printed(out):
    return {'agree': out['agree'], **out['byClass']}


def test_parity_md_states_the_counts_the_probe_prints():
    _, out = _run_probe()
    stated = _stated_counts(0)
    assert stated == _printed(out), f'PARITY.md states {stated}; the probe prints {_printed(out)}'


def _groups(out):
    """The four groups PARITY.md sorts main's differences into, counted from
    the probe's own listing, by class and input name."""
    by = {}
    for d in out['differences']:
        cls, name = d['class'], d['input']
        if cls == 'number':
            key = 'score' if name.startswith(('confidenceScore=', 'scores ')) else 'field'
        elif cls in ('quoted-value', 'number+quoted-value'):
            key = cls
            if name.endswith('={"a":1}'):
                by['object'] = by.get('object', 0) + 1
        else:
            key = cls
        by[key] = by.get(key, 0) + 1
    return by


def test_parity_md_states_the_totals_and_groups_the_probe_prints():
    _, out = _run_probe()
    with open(_PARITY, encoding='utf-8') as fh:
        parity = fh.read()

    def stated(pattern):
        m = re.search(pattern, parity)
        assert m, f'PARITY.md no longer states {pattern!r}'
        return [int(g) for g in m.groups()]
    assert stated(r'## Handed envelopes .*?; (\d+) inputs still differ') == [out['differ']]
    assert stated(r'Out of (\d+) inputs, (\d+) still differ') == [out['inputs'], out['differ']]
    g = _groups(out)
    assert stated(r'cannot hold one\*\* \((\d+) `number` inputs\)') == [g.get('field', 0)]
    assert stated(r'A valid score\*\* \((\d+) `number` inputs\)') == [g.get('score', 0)]
    assert stated(r'in a refusal\*\* \((\d+) `quoted-value` and (\d+)\s+`number\+quoted-value` inputs\)') == \
        [g.get('quoted-value', 0), g.get('number+quoted-value', 0)]
    assert stated(r'The (\d+) object inputs') == [g.get('object', 0)]
    assert stated(r'name in a message\*\* \((\d+) `field-name` inputs\)') == [g.get('field-name', 0)]
    # Every difference is in one of the four groups.
    assert sum(g.get(k, 0) for k in ('field', 'score', 'quoted-value', 'number+quoted-value', 'field-name')) \
        == out['differ']


def _copy_primitives(dest):
    # The source files only: the probe needs no node_modules.
    for lang, ext in (('js', '.mjs'), ('python', '.py')):
        src = os.path.join(_ROOT, 'primitives', lang)
        os.makedirs(os.path.join(dest, 'primitives', lang))
        for name in os.listdir(src):
            if name.endswith(ext):
                shutil.copy(os.path.join(src, name), os.path.join(dest, 'primitives', lang, name))


def test_the_probe_sees_an_outcome_difference_when_one_twin_drops_taint(tmp_path):
    # Without this, a probe that compared nothing would pass the test above.
    _copy_primitives(tmp_path)
    prov = tmp_path / 'primitives' / 'python' / 'provenance.py'
    text = prov.read_text(encoding='utf-8')
    needle = "    return _field(meta, 'derived_from_mock') is True or _field(meta, 'source') == 'mock'\n"
    assert needle in text, 'provenance.taints changed; update the mutation this test applies'
    prov.write_text(text.replace(needle, '    return False\n'), encoding='utf-8')
    code, out = _run_probe('--root', str(tmp_path))
    assert out['byClass'].get('outcome', 0) > 0 and code == 1


def test_parity_md_states_the_counts_the_probe_prints_before_525s_fix(tmp_path):
    # Needs the history: CI's shallow checkout skips it, a full clone runs it.
    have = subprocess.run(['git', 'cat-file', '-e', _PRE_525 + '^{commit}'], cwd=_ROOT, capture_output=True)
    if have.returncode != 0:
        pytest.skip(f'{_PRE_525} is not in this clone (a shallow checkout); fetch the history to run it')
    tree = subprocess.run(['git', 'archive', _PRE_525, 'primitives/js', 'primitives/python'],
                          cwd=_ROOT, capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-C', str(tmp_path)], input=tree, check=True)
    code, out = _run_probe('--root', str(tmp_path))
    stated = _stated_counts(1)
    assert stated == _printed(out), f'PARITY.md states {stated}; the probe prints {_printed(out)}'
    assert code == 1
