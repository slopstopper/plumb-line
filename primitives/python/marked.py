"""marked — thin wrapper sugar over the provenance law. The law lives in provenance.py."""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import combine_provenance, make_meta
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from provenance import combine_provenance, make_meta

# Only these keys may be supplied as overrides to derive(). lineage and
# weakest_source always come from the computed combine_provenance result;
# derived_from_mock taint cannot be cleared through an override.
_OVERRIDE_KEYS = {'source', 'confidence', 'confidence_score', 'basis', 'adapter'}

def mark(value, **meta_input):
    return {'value': value, 'meta': make_meta(**meta_input)}

def unwrap(marked):
    return marked['value']

def meta_of(marked):
    return marked['meta']

def derive(inputs, fn, **meta_override):
    value = fn(*[unwrap(i) for i in inputs])
    combined = combine_provenance(*[meta_of(i) for i in inputs])
    merged = dict(combined)
    for key in _OVERRIDE_KEYS:
        if key in meta_override:
            merged[key] = meta_override[key]
    merged['derived_from_mock'] = combined['derived_from_mock'] or bool(meta_override.get('derived_from_mock'))
    return {'value': value, 'meta': merged}
