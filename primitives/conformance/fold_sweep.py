#!/usr/bin/env python3
"""fold_sweep — the case-fold sweep across Unicode versions (#625, #642).

Compares, one code point at a time, how the running Node and the running
Python read every code point except the surrogates, as the hooks' case-alias
check reads them (``fold`` and ``UNKNOWN`` in
``adapters/js/hooks/branch-guard.mjs``; ``_fold`` and ``_unknown`` in
``adapters/python/hooks/branch_guard.py``). PARITY.md, "Case folding across
Unicode versions", cites the figures this prints, as a dated measurement on
named runtimes.

    python3 primitives/conformance/fold_sweep.py            # counts
    python3 primitives/conformance/fold_sweep.py --verbose  # and the code points behind them
    python3 primitives/conformance/fold_sweep.py --json     # machine-readable

To measure another pair, run it with that Python, with that Node first on
``PATH``. It exits 1 when a premise of the hooks' rule fails on this pair
(``foldDiffers`` or ``foldNotOne`` above 0), or when the JS half's class
rule disagrees with ``unicodedata.combining`` (``markRuleMisses`` above 0),
else 0. Without ``node`` on ``PATH`` it stops with a message.

**What is counted.**

- ``knownTo``: code points one runtime knows (not ``Cn``) and the other does
  not. The hooks match a code point the runtime does not know as any one
  character.
- ``foldDiffers``: code points both know whose fold (NFC, then upper, then
  lower case) differs between them.
- ``foldNotOne``: code points one runtime does not know, whose fold in the
  runtime that knows them is not exactly one code point. The other runtime
  folds them to themselves, one code point, so the one-for-one match would
  miss.
- ``composesIn``: primary composites one runtime composes from their NFD and
  the other does not (the composition route of #642's fail-open).
- ``reorderingMarks``: code points one runtime knows to have a canonical
  combining class other than 0, and the other does not know at all (the
  reordering route). JS has no API for the class, so the JS half finds it
  through NFD's canonical ordering, and this half checks that rule against
  ``unicodedata.combining`` on every code point Python knows that is its
  own NFD (``markRuleMisses``). Each such mark can fail open, given a following mark
  of a lower class that composes with the base.
- ``reorderingMarksAcute``: those of them that PARITY.md's example reaches,
  ``e`` + mark + U+0301: a class other than 0 and 230. The figures first
  cited for #625 (18 and 5) counted these alone.

**Lineage.** The figures PARITY.md cited for #625 came from a check run on
2026-10-03 that was not committed (the v0.12.1 dogfood self-audit). This is a
reconstruction of that check; its output names the checkout's commit and the
runtimes it compared.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))


# --- this runtime -------------------------------------------------------------

def fold(name):
    """As the Python hook folds a name (``_fold`` in branch_guard.py)."""
    return unicodedata.normalize('NFC', str(name)).upper().lower()


def unknown(c):
    """As the Python hook tells a code point it does not know (``_unknown``)."""
    return unicodedata.category(c) == 'Cn'


def reorders(c):
    """The JS half's rule for a combining class other than 0, run here so it
    can be checked against ``unicodedata.combining`` (``reorders`` in
    fold-sweep.mjs)."""
    def nfd(s):
        return unicodedata.normalize('NFD', s)
    return nfd('x' + c + '\u0334') != 'x' + c + '\u0334' or nfd('x\u0345' + c) != 'x\u0345' + c


def acute_moves(c):
    """Whether ``c`` has a combining class other than 0 and 230, the marks
    PARITY.md's example reaches: in ``e`` + ``c`` + U+0301, NFC then moves
    U+0301 before ``c`` (a class above 230) or composes it with ``e`` across
    ``c`` (a class below). Found as ``reorders`` is, against U+0301's class
    230: ``x`` + ``c`` + U+0301 reorders under NFD when ``c``'s class is
    above 230, and ``x`` + U+0301 + ``c`` when it is from 1 to 229
    (``acuteMoves`` in fold-sweep.mjs)."""
    def nfd(s):
        return unicodedata.normalize('NFD', s)
    return nfd('x' + c + '\u0301') != 'x' + c + '\u0301' or nfd('x\u0301' + c) != 'x\u0301' + c


def _code_points():
    return (cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF)


def python_tables():
    """This Python's reading, in the JS half's shape, plus the code points
    where the reorder rule and ``unicodedata.combining`` disagree."""
    known, folds, marks, acute, composites, misses = set(), {}, set(), set(), {}, []
    for cp in _code_points():
        c = chr(cp)
        if unknown(c):
            continue
        known.add(cp)
        f = fold(c)
        if f != c:
            folds[cp] = f
        d = unicodedata.normalize('NFD', c)
        if d == c:
            if reorders(c):
                marks.add(cp)
                if acute_moves(c):
                    acute.add(cp)
            if reorders(c) != (unicodedata.combining(c) != 0) or \
                    (reorders(c) and acute_moves(c)) != (unicodedata.combining(c) not in (0, 230)):
                misses.append(cp)
        elif unicodedata.normalize('NFC', d) == c:
            composites[cp] = d
    return {'known': known, 'folds': folds, 'marks': marks, 'acute': acute, 'composites': composites}, misses


def node_tables():
    try:
        proc = subprocess.run(['node', os.path.join(_HERE, 'fold-sweep.mjs')],
                              capture_output=True, text=True, check=False)
    except OSError as e:  # no node on PATH
        raise SystemExit(f'fold-sweep.mjs could not be run: {e}')
    if proc.returncode != 0:
        raise SystemExit(f'fold-sweep.mjs failed ({proc.returncode}):\n{proc.stderr}')
    raw = json.loads(proc.stdout)
    known = set()
    for lo, hi in raw['known']:
        known.update(range(lo, hi + 1))
    return {'node': raw['node'], 'unicode': raw['unicode'], 'known': known,
            'folds': {int(k): v for k, v in raw['folds'].items()},
            'marks': set(raw['marks']), 'acute': set(raw['acute']),
            'composites': {int(k): v for k, v in raw['composites'].items()}}


def _git(*args):
    try:
        proc = subprocess.run(['git', '-C', _REPO, *args], capture_output=True, text=True, check=False)
    except OSError:  # no git on PATH
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


# --- the comparison -------------------------------------------------------------

def compare(js, py, misses):
    """The counts and the code points behind them, for one Node and one Python."""
    def fold_of(t, cp):
        return t['folds'].get(cp, chr(cp))

    both = js['known'] & py['known']
    only = {'node': sorted(js['known'] - py['known']), 'python': sorted(py['known'] - js['known'])}
    fold_differs = sorted(cp for cp in both if fold_of(js, cp) != fold_of(py, cp))
    fold_not_one = sorted([cp for cp in only['node'] if len(fold_of(js, cp)) != 1]
                          + [cp for cp in only['python'] if len(fold_of(py, cp)) != 1])

    composes = {
        # Node's composites, each NFC'd by this Python.
        'node': sorted(cp for cp, d in js['composites'].items() if unicodedata.normalize('NFC', d) != chr(cp)),
        # Python's composites that Node does not list with the same NFD: NFC
        # composes only to a composite whose decomposition it knows.
        'python': sorted(cp for cp, d in py['composites'].items() if js['composites'].get(cp) != d),
    }
    marks = {'node': sorted(js['marks'] - py['known']), 'python': sorted(py['marks'] - js['known'])}
    acute = {'node': sorted(js['acute'] - py['known']), 'python': sorted(py['acute'] - js['known'])}
    return {
        'codePoints': sum(1 for _ in _code_points()),
        'knownTo': {k: len(v) for k, v in only.items()},
        'foldDiffers': len(fold_differs),
        'foldNotOne': len(fold_not_one),
        'composesIn': {k: len(v) for k, v in composes.items()},
        'reorderingMarks': {k: len(v) for k, v in marks.items()},
        'reorderingMarksAcute': {k: len(v) for k, v in acute.items()},
        'markRuleMisses': len(misses),
        'detail': {'foldDiffers': fold_differs, 'foldNotOne': fold_not_one,
                   'composesIn': composes, 'reorderingMarks': marks, 'reorderingMarksAcute': acute,
                   'markRuleMisses': misses},
    }


def run():
    js = node_tables()
    py, misses = python_tables()
    commit = _git('rev-parse', 'HEAD')
    status = _git('status', '--porcelain', '--', 'primitives/conformance') if commit else None
    res = {'measured': {'commit': commit, 'dirty': None if status is None else bool(status),
                        'node': js['node'], 'nodeUnicode': js['unicode'],
                        'python': platform.python_version(), 'pythonUnicode': unicodedata.unidata_version}}
    res.update(compare(js, py, misses))
    return res


def _name(cp):
    return unicodedata.name(chr(cp), '(not known to this Python)')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--json', action='store_true', help='print the result as JSON')
    ap.add_argument('--verbose', action='store_true', help='list the code points behind each count')
    args = ap.parse_args(argv)
    res = run()
    m = res['measured']
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        tree = 'no commit' if m['commit'] is None else \
            m['commit'] + (', primitives/conformance/ has uncommitted changes' if m['dirty'] else '')
        print(f'case-fold sweep: {res["codePoints"]} code points, Node {m["node"]} (Unicode {m["nodeUnicode"]}) '
              f'vs Python {m["python"]} (Unicode {m["pythonUnicode"]})')
        print(f'  checkout: {tree}')
        print(f'  known to Node only:   {res["knownTo"]["node"]}')
        print(f'  known to Python only: {res["knownTo"]["python"]}')
        print(f'  fold differs where both know:                     {res["foldDiffers"]}')
        print(f'  fold not one code point where one does not know: {res["foldNotOne"]}')
        print(f'  composes in Node only:   {res["composesIn"]["node"]}')
        print(f'  composes in Python only: {res["composesIn"]["python"]}')
        print(f'  reordering marks Python does not know: {res["reorderingMarks"]["node"]}')
        print(f'  reordering marks Node does not know:   {res["reorderingMarks"]["python"]}')
        print(f'    of which e + mark + U+0301 reaches: Python {res["reorderingMarksAcute"]["node"]}, '
              f'Node {res["reorderingMarksAcute"]["python"]}')
        print(f'  reorder rule misses (against unicodedata.combining): {res["markRuleMisses"]}')
        if args.verbose:
            d = res['detail']
            for label, cps in (('fold differs', d['foldDiffers']), ('fold not one', d['foldNotOne']),
                               ('composes in Node only', d['composesIn']['node']),
                               ('composes in Python only', d['composesIn']['python']),
                               ('reordering mark Python does not know', d['reorderingMarks']['node']),
                               ('reordering mark Node does not know', d['reorderingMarks']['python']),
                               ('reorder rule miss', d['markRuleMisses'])):
                for cp in cps:
                    print(f'  [{label}] U+{cp:04X} {_name(cp)}')
    return 1 if res['foldDiffers'] or res['foldNotOne'] or res['markRuleMisses'] else 0


if __name__ == '__main__':
    sys.exit(main())
