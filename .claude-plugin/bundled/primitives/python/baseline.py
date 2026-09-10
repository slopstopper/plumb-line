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
import os
import re
import sys
import tempfile
from datetime import date as _date

try:  # installed as a package (plumb_line_provenance)
    from .provenance import PROVENANCE_VERSION
    from .audit import validate_envelope
    from .marked import meta_of, unwrap
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    PROVENANCE_VERSION = _prov.PROVENANCE_VERSION
    from audit import validate_envelope
    from marked import meta_of, unwrap

BASELINE_FORMAT = 'v1'
KNOWN_BASELINE_FORMATS = {'v1'}
DEFAULT_DIR = os.path.join('.plumb-line', 'baselines')
NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')
STEP_FIELDS = ['source', 'confidence', 'confidenceScore', 'derivedFromMock', 'of']
TOP_FIELDS = ['source', 'confidence', 'confidenceScore', 'derivedFromMock']
_RECORD_KEYS = ['baseline-format', 'name', 'provenanceVersion', 'value', 'meta', 'history']
_DATE_RE = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')

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


# ---------- record ----------

def to_record(name, marked, history):
    wire = dict(to_wire(meta_of(marked)))
    provenance_version = wire.pop('provenanceVersion', None)
    return {'baseline-format': BASELINE_FORMAT, 'name': name, 'provenanceVersion': provenance_version,
            'value': unwrap(marked), 'meta': wire, 'history': history}


def validate_baseline(record):
    """P7 validator for a parsed record. [] when valid; never raises."""
    if not isinstance(record, dict):
        return ['not a baseline record']
    issues = []
    for k in _RECORD_KEYS:
        if k not in record:
            issues.append(f'missing required key: {k}')
    if 'baseline-format' in record and record['baseline-format'] not in KNOWN_BASELINE_FORMATS:
        issues.append(f'unknown baseline-format {json.dumps(record["baseline-format"])} '
                      f'(this library models {", ".join(sorted(KNOWN_BASELINE_FORMATS))})')
    if 'name' in record and not (isinstance(record['name'], str) and NAME_RE.match(record['name'])):
        issues.append(f'name must match {NAME_RE.pattern}')
    if 'provenanceVersion' in record and (isinstance(record['provenanceVersion'], bool)
                                          or not isinstance(record['provenanceVersion'], int)):
        issues.append('provenanceVersion must be an integer')
    if 'meta' in record:
        meta = dict(record['meta']) if isinstance(record['meta'], dict) else record['meta']
        if isinstance(meta, dict):
            meta['provenanceVersion'] = record.get('provenanceVersion')
            meta = from_wire(meta)
        for i in validate_envelope(meta):
            issues.append(f'meta: {i}')
    if 'history' in record:
        h = record['history']
        if not isinstance(h, list) or not h:
            issues.append('history must be a non-empty array')
        else:
            for i, e in enumerate(h):
                if not isinstance(e, dict):
                    issues.append(f'history[{i}] must be an object')
                    continue
                if not isinstance(e.get('date'), str) or not _DATE_RE.match(e['date']):
                    issues.append(f'history[{i}].date must be YYYY-MM-DD')
                if not isinstance(e.get('because'), str) or not e['because'].strip():
                    issues.append(f'history[{i}].because must be a non-empty string')
                if not isinstance(e.get('change'), str):
                    issues.append(f'history[{i}].change must be a string')
    return issues


# ---------- file store ----------

def _abs_dir(dir):
    return os.path.abspath(dir if dir is not None else DEFAULT_DIR)


def _path_for(dir, name):
    return os.path.join(_abs_dir(dir), f'{name}.json')


def _require_name(name):
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError(f'baseline name must match {NAME_RE.pattern}, got {name!r}')


def _read_record(dir, name):
    path = _path_for(dir, name)
    if not os.path.exists(path):
        return {'status': 'missing', 'path': path}
    try:
        with open(path, encoding='utf-8') as fh:
            parsed = json.load(fh)
    except (OSError, ValueError) as e:
        return {'status': 'invalid', 'path': path, 'issues': [f'cannot parse: {e}']}
    issues = validate_baseline(parsed)
    if issues:
        return {'status': 'invalid', 'path': path, 'issues': issues}
    if parsed.get('name') != name:
        return {'status': 'invalid', 'path': path,
                'issues': [f'name {json.dumps(parsed.get("name"))} does not match the filename']}
    return {'status': 'ok', 'path': path, 'record': parsed}


def check(name, marked, dir=None):
    _require_name(name)
    envelope_issues = validate_envelope(meta_of(marked))
    if envelope_issues:
        return {'status': 'invalid-envelope', 'name': name, 'dir': _abs_dir(dir), 'findings': [],
                'summary': 'none', 'issues': envelope_issues}
    read = _read_record(dir, name)
    if read['status'] != 'ok':
        return {'status': read['status'], 'name': name, 'dir': _abs_dir(dir), 'path': read['path'],
                'findings': [], 'summary': 'none', 'issues': read.get('issues', [])}
    findings = compare(read['record'], to_wire(meta_of(marked)), unwrap(marked), PROVENANCE_VERSION)
    return {'status': 'drift' if findings else 'match', 'name': name, 'dir': _abs_dir(dir),
            'path': read['path'], 'findings': findings, 'summary': summarize(findings)}


def report_text(report):
    head = f"baseline {report['name']} ({report['dir']}): {report['status']}"
    s = report['status']
    if s == 'match':
        return head
    if s == 'drift':
        return '\n'.join([head] + [f'  {f["text"]}' for f in report['findings']] + [
            f'  accept with: update({json.dumps(report["name"])}, <marked>, because="<why the new state is correct>", dir={json.dumps(report["dir"])})'])
    if s == 'missing':
        return '\n'.join([head, f'  no baseline file at {report["path"]}',
            f'  record one with: update({json.dumps(report["name"])}, <marked>, because="<why this state is correct>", dir={json.dumps(report["dir"])})'])
    if s == 'invalid':
        return '\n'.join([head, f'  {report["path"]} is not a valid baseline record:'] + [f'    {i}' for i in report['issues']])
    if s == 'invalid-envelope':
        return '\n'.join([head, "  the marked value's envelope is not valid:"] + [f'    {i}' for i in report['issues']])
    return head


def assert_baseline(name, marked, dir=None):
    report = check(name, marked, dir=dir)
    if report['status'] != 'match':
        raise AssertionError(report_text(report))


def update(name, marked, because=None, dir=None, date=None):
    _require_name(name)
    if not isinstance(because, str) or not because.strip():
        raise ValueError('update requires `because`: a non-empty explanation of why the new state is correct')
    envelope_issues = validate_envelope(meta_of(marked))
    if envelope_issues:
        raise ValueError(f'cannot pin an invalid envelope: {"; ".join(envelope_issues)}')
    value = unwrap(marked)
    if not is_json_value(value):
        raise ValueError('cannot pin a value that is not JSON-serialisable')
    read = _read_record(dir, name)
    if read['status'] == 'invalid':
        raise ValueError(f'refusing to overwrite an invalid baseline at {read["path"]}: {"; ".join(read["issues"])}')
    today = date or _date.today().isoformat()
    if read['status'] == 'missing':
        history, change = [], 'initial'
    else:
        history = list(read['record']['history'])
        change = summarize(compare(read['record'], to_wire(meta_of(marked)), value, PROVENANCE_VERSION))
    history.append({'date': today, 'because': because.strip(), 'change': change})
    record = to_record(name, marked, history)
    abs_dir = _abs_dir(dir)
    os.makedirs(abs_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'.{name}.', suffix='.tmp', dir=abs_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(canonical_json(record))
        os.replace(tmp, _path_for(dir, name))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return record


def list_baselines(dir=None):
    abs_dir = _abs_dir(dir)
    if not os.path.isdir(abs_dir):
        return []
    return sorted(f[:-len('.json')] for f in os.listdir(abs_dir)
                  if f.endswith('.json') and not f.startswith('.'))


def show(name, dir=None):
    _require_name(name)
    read = _read_record(dir, name)
    if read['status'] == 'missing':
        raise LookupError(f'no baseline named {name} in {_abs_dir(dir)}')
    if read['status'] == 'invalid':
        raise ValueError(f'{read["path"]} is not a valid baseline record: {"; ".join(read["issues"])}')
    return read['record']


# ---------- CLI (inspection only; see docs/adr/0015) ----------

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='baseline', description='inspect plumb-line baseline records')
    ap.add_argument('cmd', nargs='?', choices=['list', 'show', 'validate'])
    ap.add_argument('name', nargs='?')
    ap.add_argument('--dir', default=None)
    args = ap.parse_args(argv)
    abs_dir = _abs_dir(args.dir)
    if args.cmd == 'list':
        if not os.path.isdir(abs_dir):
            print(f'no baselines directory at {abs_dir}')
            return 0
        names = list_baselines(dir=abs_dir)
        for n in names:
            print(n)
        print(f'{len(names)} baseline(s) in {abs_dir}')
        return 0
    if args.cmd == 'show':
        if not args.name:
            print('usage: baseline show <name> [--dir D]', file=sys.stderr)
            return 2
        try:
            rec = show(args.name, dir=abs_dir)
        except (LookupError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f'{rec["name"]}  (baseline-format {rec["baseline-format"]}, wire v{rec["provenanceVersion"]})')
        print(f'value: {compact_json(rec["value"])}')
        for k in ('source', 'confidence', 'confidenceScore', 'derivedFromMock', 'weakestSource'):
            if k in rec['meta']:
                print(f'{k}: {compact_json(rec["meta"][k])}')
        steps = rec['meta']['lineage']
        print(f'lineage: {len(steps)} step(s)')
        for i, s in enumerate(steps):
            tainted = ' tainted' if s.get('derivedFromMock') else ''
            score = f' score {s["confidenceScore"]}' if 'confidenceScore' in s else ''
            print(f'  [{i}] {s.get("source")}/{s.get("confidence")}{tainted}{score}')
        print('history:')
        for h in rec['history']:
            print(f'  {h["date"]}  {h["change"]}  {h["because"]}')
        return 0
    if args.cmd == 'validate':
        if not os.path.isdir(abs_dir):
            print(f'no baselines directory at {abs_dir}; 0 files validated')
            return 0
        files = sorted(f for f in os.listdir(abs_dir) if f.endswith('.json') and not f.startswith('.'))
        bad = 0
        for f in files:
            try:
                with open(os.path.join(abs_dir, f), encoding='utf-8') as fh:
                    issues = validate_baseline(json.load(fh))
            except (OSError, ValueError) as e:
                issues = [f'cannot parse: {e}']
            if issues:
                bad += 1
                print(f'✗ {f}')
                for i in issues:
                    print(f'    {i}')
            else:
                print(f'✓ {f}')
        print(f'{bad} of {len(files)} invalid' if bad else f'{len(files)} file(s) valid')
        return 1 if bad else 0
    print('usage: baseline <list|show <name>|validate> [--dir D]', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
