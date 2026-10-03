#!/usr/bin/env python3
"""handed_probe — the handed-envelope differential probe (#525, #594).

Feeds the same handed inputs to both twins' ``combine``, then audits and
guards each result, and counts the inputs whose records differ. A handed
envelope is one a caller built or deserialised itself, not one ``makeMeta``
made, so it can carry anything JSON can write. PARITY.md, "Handed
envelopes", cites the counts this prints; scripts/test_handed_probe.py checks
that it states them as printed.

    python3 primitives/conformance/handed_probe.py            # counts
    python3 primitives/conformance/handed_probe.py --verbose  # and each difference
    python3 primitives/conformance/handed_probe.py --json     # machine-readable
    python3 primitives/conformance/handed_probe.py --root DIR # probe another tree

It exits 1 when any input differs in outcome, else 0. Its output, printed
and ``--json`` (``probed``), names what the counts were measured on: the
probed tree, its commit when the tree is a git checkout, and the Node and
Python versions run, whose JSON parsers make the ``number`` class.

**What is compared.** Each input is JSON text, and each twin parses it with
its own JSON parser, as a caller in that language would. A twin's record of
an input is its combined envelope (camelCase keys), its audit issues and its
guard verdict (a pass, or the refusal's reasons): the values the twin holds,
carried as JSON. A number JSON cannot write (``-0``, an infinity, ``NaN``)
is tagged ``{"$number": "-0"}`` and so on by both halves, so that neither
serializer's rendering of it (``JSON.stringify`` writes ``0`` and ``null``)
hides or makes a difference. A throw is recorded as one; its text, the
record's top-level ``detail``, is not compared. The records are compared leaf
by leaf; each differing leaf is one of:

- ``field-name``: two strings that agree once Python's snake_case field names
  are written in camelCase (an audit or guard message naming the field).
- ``number``: two numbers that are the same IEEE-754 double, held as
  different values. Each language's JSON parser makes these from the same
  text: Python reads ``1.0`` as a float and JS as its one number type, ``-0``
  as the integer 0 where JS reads -0, and an integer beyond double range
  exactly where JS reads Infinity. ``combine`` keeps them verbatim on a step,
  and Python's ``min`` keeps whichever zero came first.
- ``quoted-value``: two messages that are the same apart from one value they
  quote, each in its own language's JSON rendering (``1e-07`` against
  ``1e-7``, ``{"a": 1}`` against ``{"a":1}``), as a guard refusal quotes it.
- ``outcome``: any other difference — taint, an id, a verdict, the record's
  shape, one twin throwing, other message text.

An input is classed by its leaves: ``agree``; ``field-name``, ``number`` or
``quoted-value``, or a ``+``-joined mix of them; or ``outcome`` if any leaf
is.

**The corpus** is generated below, not sampled: a ladder of JSON values that
handed envelopes carry in practice or by accident, set in turn into each field
``combine`` reads, into a lineage step, and in place of the input itself.

**Lineage.** #525's first probe (28 inputs) and its review's (143 inputs)
were not committed, so their counts in PARITY.md could not be re-run (#594).
This is a reconstruction from #525's record, not either of them; its counts
replace theirs.
"""
import argparse
import json
import math
import os
import platform
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

# camelCase (JSON) <-> snake_case (Python envelope), as in
# primitives/python/tests/test_conformance.py.
_KEY = {
    'confidenceScore': 'confidence_score',
    'derivedFromMock': 'derived_from_mock',
    'weakestSource': 'weakest_source',
    'provenanceVersion': 'provenance_version',
}
_CAMEL = {v: k for k, v in _KEY.items()}

# --- the corpus -------------------------------------------------------------

# (name, JSON text). Text, not values: each twin's parser must read it.
VALUES = [
    ('null', 'null'),
    ('true', 'true'),
    ('false', 'false'),
    ('0', '0'),
    ('-0', '-0'),
    ('-0.0', '-0.0'),
    ('1', '1'),
    ('1.0', '1.0'),
    ('1e-7', '1e-7'),
    ('0.5', '0.5'),
    ('1e400', '1e400'),
    ('10**400', '1' + '0' * 400),   # an integer beyond double range, under Python's 4,300-digit limit
    ('""', '""'),
    ('"x"', '"x"'),
    ('"mock"', '"mock"'),
    ('lone surrogate', '"\\ud800"'),
    ('[]', '[]'),
    ('[1]', '[1]'),
    ('{}', '{}'),
    ('{"a":1}', '{"a": 1}'),
]

# A clean envelope and a clean lineage step, as {key: JSON text}.
_BASE = {'source': '"real"', 'confidence': '"high"', 'derivedFromMock': 'false',
         'lineage': '[]', 'provenanceVersion': '2'}
_STEP = {'of': '"input"', 'source': '"real"', 'confidence': '"high"',
         'derivedFromMock': 'false', 'id': '"sha256:000000000000"'}
_ENVELOPE_FIELDS = ('source', 'confidence', 'confidenceScore', 'derivedFromMock', 'lineage')
_STEP_FIELDS = ('source', 'derivedFromMock', 'id')


def _obj(fields):
    """A JSON object's text from {key: value text}; a value of None leaves the key out."""
    return '{' + ', '.join(f'{json.dumps(k)}: {v}' for k, v in fields.items() if v is not None) + '}'


def _with(base, key, value):
    out = dict(base)
    out[key] = value
    return out


def corpus():
    """Every probe input, as (name, JSON text of the array of combine inputs)."""
    base = _obj(_BASE)
    out = []
    # 1. Each field combine reads, set to each value, or left out.
    # A value the clean envelope or step already carries is skipped: that input
    # would be the clean one again.
    for field in _ENVELOPE_FIELDS:
        for name, v in VALUES + [('absent', None)]:
            if v == _BASE.get(field):
                continue
            out.append((f'{field}={name}', f'[{_obj(_with(_BASE, field, v))}]'))
    # 2. A value that is not an envelope, alone and beside a clean one.
    for name, v in VALUES:
        out.append((f'input={name}', f'[{v}]'))
        out.append((f'clean,input={name}', f'[{base}, {v}]'))
    # 3. A lineage step that is each value, then each step field set to each value.
    for name, v in VALUES:
        out.append((f'step={name}', f'[{_obj(_with(_BASE, "lineage", f"[{v}]"))}]'))
    for field in _STEP_FIELDS:
        for name, v in VALUES:
            if v == _STEP[field]:
                continue
            step = _obj(_with(_STEP, field, v))
            out.append((f'step.{field}={name}', f'[{_obj(_with(_BASE, "lineage", f"[{step}]"))}]'))
    # 4. Inputs whose result once depended on their order in one twin (#525
    # review): Python's min over 0 and -0.0, and ids sorted by UTF-16 unit in
    # JS. Each order is compared across the twins, not with the other order.
    def scored(score):
        return _obj(_with(_BASE, 'confidenceScore', score))

    def with_id(i):
        return _obj(_with(_BASE, 'lineage', f'[{_obj(_with(_STEP, "id", i))}]'))
    out.append(('scores 0,-0.0', f'[{scored("0")}, {scored("-0.0")}]'))
    out.append(('scores -0.0,0', f'[{scored("-0.0")}, {scored("0")}]'))
    # U+FFFF sorts after an astral character by UTF-16 unit, before it by code point.
    out.append(('ids U+FFFF,U+1F600', f'[{with_id(json.dumps(chr(0xFFFF)))}, {with_id(json.dumps(chr(0x1F600)))}]'))
    out.append(('ids U+1F600,U+FFFF', f'[{with_id(json.dumps(chr(0x1F600)))}, {with_id(json.dumps(chr(0xFFFF)))}]'))
    # The families overlap (`lineage=[1]` is `step=1`): each text once, under
    # its first name, so no input is counted twice.
    seen = set()
    return [(n, t) for n, t in out if not (t in seen or seen.add(t))]


# --- the two twins ----------------------------------------------------------

def _to_snake(d):
    return {_KEY.get(k, k): v for k, v in d.items()}


def _handed_to_snake(m):
    """A handed input as a Python caller would build it: snake_case keys on
    the envelope and on each dict step. Anything else is handed as it is."""
    if not isinstance(m, dict):
        return m
    out = _to_snake(m)
    if isinstance(out.get('lineage'), list):
        out['lineage'] = [_to_snake(s) if isinstance(s, dict) else s for s in out['lineage']]
    return out


def _to_camel(d):
    return {_CAMEL.get(k, k): v for k, v in d.items()} if isinstance(d, dict) else d


def _python_records(texts, root):
    # Imported here, not at module level, so importing this module (as its
    # test does) never puts the primitive's flat module names in sys.modules.
    sys.path.insert(0, os.path.join(root, 'primitives', 'python'))
    import provenance
    import audit
    import guard as guard_mod
    refused_type = getattr(guard_mod, 'ProvenanceRefused', None)

    def record(text):
        inputs = [_handed_to_snake(m) for m in json.loads(text)]
        try:
            out = provenance.combine_provenance(*inputs)
        except Exception as e:  # a throw is a recorded outcome, not a probe failure
            return {'combine': {'raises': True}, 'detail': repr(e)}
        env = _to_camel(dict(out))
        if isinstance(env.get('lineage'), list):
            env['lineage'] = [_to_camel(s) for s in env['lineage']]
        r = {'combine': env}
        try:
            r['audit'] = audit.audit_meta(out)
        except Exception as e:
            r['audit'] = {'raises': True}
            r['detail'] = repr(e)
        try:
            guard_mod.guard({'value': 1, 'meta': out})
            r['guard'] = {'pass': True}
        except Exception as e:
            if refused_type is not None and isinstance(e, refused_type):
                r['guard'] = {'refused': list(e.reasons)}
            else:
                r['guard'] = {'raises': True}
                r['detail'] = repr(e)
        # Carried as JSON, as the JS half's records are, with the numbers JSON
        # cannot write tagged the same way (tagNumbers in handed-probe.mjs).
        return json.loads(json.dumps(tag_numbers(r), default=repr))
    return [record(t) for t in texts]


def tag_numbers(v):
    """``v`` with each number JSON cannot write — ``-0.0``, an infinity,
    ``NaN`` — replaced by ``{"$number": <its JS name>}``, as the JS half's
    tagNumbers replaces it. Any other value is kept as it is."""
    if isinstance(v, dict):
        return {k: tag_numbers(x) for k, x in v.items()}
    if isinstance(v, list):
        return [tag_numbers(x) for x in v]
    if isinstance(v, float):
        if math.isnan(v):
            return {'$number': 'NaN'}
        if math.isinf(v):
            return {'$number': 'Infinity' if v > 0 else '-Infinity'}
        if v == 0 and math.copysign(1, v) < 0:
            return {'$number': '-0'}
    return v


def _js_records(texts, root):
    proc = subprocess.run(['node', os.path.join(_HERE, 'handed-probe.mjs'), root],
                          input=json.dumps(texts), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f'handed-probe.mjs failed ({proc.returncode}):\n{proc.stderr}')
    return json.loads(proc.stdout)


# --- the comparison ---------------------------------------------------------

def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _as_double(x):
    try:
        return float(x)
    except OverflowError:  # an int beyond double range, as JSON.parse reads it
        return math.inf if x > 0 else -math.inf


_TAGGED = {'-0': -0.0, 'Infinity': math.inf, '-Infinity': -math.inf, 'NaN': math.nan}


def _tagged(x):
    """The number a ``{"$number": ...}`` tag stands for, else None."""
    if isinstance(x, dict) and len(x) == 1 and x.get('$number') in _TAGGED:
        return _TAGGED[x['$number']]
    return None


def _numeric(x):
    return _is_number(x) or _tagged(x) is not None


def _same_double(py, js):
    """Whether two numbers, either of them perhaps tagged, are one IEEE-754
    double (-0 and 0 are one double; NaN is never the same)."""
    def d(x):
        t = _tagged(x)
        return t if t is not None else _as_double(x)
    return d(py) == d(js)


def _same_quoted(py, js):
    """Whether two renderings of one value quoted in a message are the same
    value: each is read back as JSON (Python's ``Infinity`` too), numbers by
    their double, anything else by its canonical JSON text."""
    try:
        a, b = json.loads(py), json.loads(js)
    except ValueError:
        return False
    if _is_number(a) and _is_number(b):
        return _same_double(a, b)
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _quoted_value_only(py, js):
    """Whether two messages are the same apart from one quoted value, written
    in each language's own JSON rendering, as a guard refusal quotes it. The
    differing span is widened to the spaces around it, so the value is read
    whole (`1.0` against `1`, `{"a": 1}` against `{"a":1}`)."""
    pre = 0
    while pre < min(len(py), len(js)) and py[pre] == js[pre]:
        pre += 1
    pre = py.rfind(' ', 0, pre) + 1
    suf = 0
    while suf < min(len(py), len(js)) - pre and py[-1 - suf] == js[-1 - suf]:
        suf += 1
    tail = py[len(py) - suf:]
    cut = tail.find(' ')
    suf = suf - cut if cut >= 0 else 0
    mid_py, mid_js = py[pre:len(py) - suf], js[pre:len(js) - suf]
    return bool(mid_py and mid_js) and _same_quoted(mid_py, mid_js)


def _leaf_class(py, js):
    if isinstance(py, str) and isinstance(js, str):
        renamed = py
        for snake, camel in _CAMEL.items():
            renamed = renamed.replace(snake, camel)
        if renamed == js:
            return 'field-name'
        return 'quoted-value' if _quoted_value_only(py, js) else 'outcome'
    if _numeric(py) and _numeric(js):
        return 'number' if _same_double(py, js) else 'outcome'
    return 'outcome'


def diff(py, js, path='$'):
    """Every leaf where two records differ, as (path, class). A tagged number
    is a leaf. The record's own `detail` (an error's text) is not compared;
    a `detail` key deeper in, such as one a handed step carries, is."""
    if (isinstance(py, dict) and isinstance(js, dict)
            and _tagged(py) is None and _tagged(js) is None):
        out = []
        for k in sorted(set(py) | set(js)):
            if k == 'detail' and path == '$':
                continue
            if k not in py or k not in js:
                out.append((f'{path}.{k}', 'outcome'))
            else:
                out.extend(diff(py[k], js[k], f'{path}.{k}'))
        return out
    if isinstance(py, list) and isinstance(js, list):
        if len(py) != len(js):
            return [(path, 'outcome')]
        out = []
        for i, (a, b) in enumerate(zip(py, js)):
            out.extend(diff(a, b, f'{path}[{i}]'))
        return out
    # JSON text decides equality, so true is not 1 and 1.0 is not 1.
    if json.dumps(py, sort_keys=True) == json.dumps(js, sort_keys=True):
        return []
    return [(path, _leaf_class(py, js))]


def classify(differences):
    """One input's class from its differing leaves."""
    classes = {c for _, c in differences}
    if not classes:
        return 'agree'
    if 'outcome' in classes:
        return 'outcome'
    return '+'.join(sorted(classes))


def _git(root, *args):
    try:
        proc = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True, check=False)
    except OSError:  # no git on PATH
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def probed(root):
    """What the counts were measured on: the probed tree, its commit and the
    two runtimes whose JSON parsers read the corpus (the ``number`` class
    depends on them). ``commit`` is None unless ``root`` is the top of a git
    checkout, so a copied tree inside another repository is not credited with
    that repository's commit; ``dirty`` says whether anything under the
    tree's ``primitives/`` (the twins, and this probe when it probes its own
    checkout) differs from that commit."""
    commit = dirty = None
    top = _git(root, 'rev-parse', '--show-toplevel')
    if top is not None and os.path.realpath(top) == os.path.realpath(root):
        commit = _git(root, 'rev-parse', 'HEAD')
        if commit is not None:
            status = _git(root, 'status', '--porcelain', '--', 'primitives')
            dirty = None if status is None else bool(status)
    node = subprocess.run(['node', '--version'], capture_output=True, text=True, check=False)
    return {'root': root, 'commit': commit, 'dirty': dirty,
            'node': node.stdout.strip() if node.returncode == 0 else None,
            'python': platform.python_version()}


def run(root):
    cases = corpus()
    texts = [t for _, t in cases]
    py, js = _python_records(texts, root), _js_records(texts, root)
    by_class, differences = {}, []
    for (name, _), a, b in zip(cases, py, js):
        d = diff(a, b)
        cls = classify(d)
        if cls != 'agree':
            by_class[cls] = by_class.get(cls, 0) + 1
            differences.append({'input': name, 'class': cls, 'leaves': [p for p, _ in d],
                                'python': a, 'js': b})
    return {'probed': probed(root), 'inputs': len(cases), 'agree': len(cases) - len(differences),
            'differ': len(differences), 'byClass': by_class, 'differences': differences}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--root', default=_REPO, help='the tree whose primitives/ are probed (default: this checkout)')
    ap.add_argument('--json', action='store_true', help='print the result as JSON')
    ap.add_argument('--verbose', action='store_true', help='list each differing input and its leaves')
    args = ap.parse_args(argv)
    res = run(os.path.abspath(args.root))
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        p = res['probed']
        if p['commit'] is None:
            tree = 'no commit'
        else:
            tree = p['commit'] + (', primitives/ has uncommitted changes' if p['dirty'] else '')
        print(f'handed-envelope probe: {res["inputs"]} inputs through combine, audit and guard, JS vs Python')
        print(f'  probed: {p["root"]} ({tree}); Node {p["node"]}, Python {p["python"]}')
        print(f'  agree:  {res["agree"]}')
        print(f'  differ: {res["differ"]}')
        for cls in sorted(res['byClass']):
            print(f'    {cls}: {res["byClass"][cls]}')
        if args.verbose:
            for d in res['differences']:
                print(f'  [{d["class"]}] {d["input"]}: {", ".join(d["leaves"])}')
    return 1 if res['byClass'].get('outcome') else 0


if __name__ == '__main__':
    sys.exit(main())
