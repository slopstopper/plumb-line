"""baseline — Principle 9: golden baseline + explain-the-drift. Mirror of baseline.mjs.

Pins a marked value WITH its trust state, diffs later runs against the pin,
refuses silent drift, and requires a recorded explanation to accept a new
state. Attribution is what separates this from snapshot testing: the
envelope's lineage records each input's state at combination time, so a
drift can say which input moved. See docs/adr/0015-baseline-library-first.md
and SPEC §4. Parity with baseline.mjs is pinned by
primitives/conformance/baseline-cases.json.

The file on disk is ALWAYS the SPEC wire form (flat camelCase); this module
converts the Python nested/snake_case envelope on write and read.
"""
import json
import re

try:  # installed as a package (plumb_line_provenance)
    from .provenance import PROVENANCE_VERSION
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    PROVENANCE_VERSION = _prov.PROVENANCE_VERSION

BASELINE_FORMAT = 'v1'
NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')
STEP_FIELDS = ['source', 'confidence', 'confidenceScore', 'derivedFromMock', 'of']
TOP_FIELDS = ['source', 'confidence', 'confidenceScore', 'derivedFromMock']

_TO_WIRE = {'confidence_score': 'confidenceScore', 'derived_from_mock': 'derivedFromMock',
            'weakest_source': 'weakestSource', 'provenance_version': 'provenanceVersion'}
_FROM_WIRE = {v: k for k, v in _TO_WIRE.items()}


# ---------- wire conversion ----------

def _rename(d, table):
    out = {table.get(k, k): v for k, v in d.items()}
    if isinstance(out.get('lineage'), list):
        out['lineage'] = [{table.get(k, k): v for k, v in s.items()} if isinstance(s, dict) else s
                          for s in out['lineage']]
    return out


def to_wire(meta):
    """Python snake_case envelope -> SPEC wire form (flat camelCase)."""
    return _rename(meta, _TO_WIRE)


def from_wire(meta):
    """SPEC wire form -> Python snake_case envelope."""
    return _rename(meta, _FROM_WIRE)


# ---------- canonical JSON ----------

def canonicalize(x):
    if isinstance(x, list):
        return [canonicalize(v) for v in x]
    if isinstance(x, dict):
        return {k: canonicalize(x[k]) for k in sorted(x)}
    return x


def canonical_json(x):
    return json.dumps(canonicalize(x), indent=2, ensure_ascii=False, allow_nan=False) + '\n'


def compact_json(x):
    return json.dumps(canonicalize(x), separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def is_json_value(x):
    try:
        return deep_equal(json.loads(json.dumps(x, allow_nan=False)), x)
    except (TypeError, ValueError):
        return False


def deep_equal(a, b):
    # bool is an int subclass in Python; JSON keeps them distinct, so do we.
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(deep_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return sorted(a) == sorted(b) and all(deep_equal(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


# ---------- attribution ----------

def _finding(path, before, after, text):
    return {'path': path, 'before': before, 'after': after, 'text': text}


def _field_text(path, b, a):
    return f'{path}: {compact_json(b)} -> {compact_json(a)}'


def compare(record, wire_meta, value, running_version=PROVENANCE_VERSION):
    """Compare a pinned record against a new WIRE-form envelope + value.

    Findings come in the fixed order: version, per-step fields, lineage
    length, top-level fields not explained by a step finding, value.
    """
    f = []
    if record.get('provenanceVersion') != running_version:
        b = record.get('provenanceVersion')
        f.append(_finding('provenanceVersion', b, running_version,
                          f'pinned under wire v{b}, running v{running_version}'))
    pl = record.get('meta', {}).get('lineage') if isinstance(record.get('meta'), dict) else None
    pl = pl if isinstance(pl, list) else []
    nl = wire_meta.get('lineage') if isinstance(wire_meta, dict) else None
    nl = nl if isinstance(nl, list) else []
    touched = set()
    for i in range(min(len(pl), len(nl))):
        for field in STEP_FIELDS:
            b = pl[i].get(field) if isinstance(pl[i], dict) else None
            a = nl[i].get(field) if isinstance(nl[i], dict) else None
            if not deep_equal(b, a):
                path = f'meta.lineage[{i}].{field}'
                f.append(_finding(path, b, a, _field_text(path, b, a)))
                touched.add(field)
    if len(pl) != len(nl):
        grew = len(nl) > len(pl)
        n = abs(len(nl) - len(pl))
        k = min(len(pl), len(nl))
        f.append(_finding('meta.lineage.length', len(pl), len(nl),
                          f'lineage grew by {n} (first new step: meta.lineage[{k}])' if grew
                          else f'lineage shrank by {n} (first missing step: meta.lineage[{k}])'))
        touched.add('length')
    rmeta = record.get('meta') if isinstance(record.get('meta'), dict) else {}
    for field in TOP_FIELDS:
        b, a = rmeta.get(field), (wire_meta or {}).get(field)
        if field not in touched and not deep_equal(b, a):
            path = f'meta.{field}'
            f.append(_finding(path, b, a, _field_text(path, b, a)))
    if not deep_equal(record.get('value'), value):
        attributed = any(x['path'].startswith('meta.') for x in f)
        f.append(_finding('value', record.get('value'), value,
                          'value moved; attributed to the findings above' if attributed
                          else 'value moved with no input change'))
    return f


def summarize(findings):
    return '; '.join(x['text'] for x in findings) if findings else 'none'
