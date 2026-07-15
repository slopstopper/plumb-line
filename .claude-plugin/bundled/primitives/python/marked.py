"""marked — thin wrapper sugar over the provenance law. The law lives in provenance.py."""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import combine_provenance, make_meta
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'combine_provenance') or not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    combine_provenance, make_meta = _prov.combine_provenance, _prov.make_meta

# Only these keys may be supplied as overrides to derive(). lineage and
# weakest_source always come from the computed combine_provenance result;
# derived_from_mock taint cannot be cleared through an override.
_OVERRIDE_KEYS = {'source', 'confidence', 'confidence_score', 'basis', 'adapter'}

def mark(value, **meta_input):
    """Wrap a value with provenance metadata.

    Returns a dict with a ``value`` key holding the original value and a
    ``meta`` key holding the provenance metadata dict.

    Args:
        value: Any value to track.
        **meta_input: Keyword arguments forwarded to :func:`make_meta`
            (e.g. ``source="real"``, ``confidence="high"``).

    Returns:
        dict: ``{"value": value, "meta": {...}}``.
    """
    return {'value': value, 'meta': make_meta(**meta_input)}

def unwrap(marked):
    """Extract the raw value from a marked dict.

    Args:
        marked: A dict produced by :func:`mark` or :func:`derive`.

    Returns:
        The unwrapped value.
    """
    return marked['value']

def meta_of(marked):
    """Extract the provenance metadata from a marked dict.

    Args:
        marked: A dict produced by :func:`mark` or :func:`derive`.

    Returns:
        dict: Provenance metadata envelope.
    """
    return marked['meta']

def derive(inputs, fn, **meta_override):
    """Derive a new marked value from one or more marked inputs.

    The combination law is applied automatically: mock taint and the weakest
    confidence propagate to the result and cannot be overridden.

    Args:
        inputs: List of marked dicts produced by :func:`mark` or :func:`derive`.
        fn: Pure function applied to the unwrapped input values.
        **meta_override: Optional overrides for ``source``, ``confidence``,
            ``confidence_score``, ``basis``, or ``adapter``.
            ``derived_from_mock`` cannot be cleared via override.
            By convention ``basis`` is an operation label naming the transform
            ``fn`` (e.g. ``"aggregate.sum"``) — lineage records input states,
            not ``fn``. See SPEC §4.

    Returns:
        dict: ``{"value": ..., "meta": {...}}``.
    """
    value = fn(*[unwrap(i) for i in inputs])
    combined = combine_provenance(*[meta_of(i) for i in inputs])
    overridden = dict(combined)
    # provenance_version is stamped by make_meta itself from the constant; it is
    # not one of make_meta's parameters, so it must not be re-forwarded here.
    overridden.pop('provenance_version', None)
    for key in _OVERRIDE_KEYS:
        if key in meta_override:
            overridden[key] = meta_override[key]
    overridden['derived_from_mock'] = combined['derived_from_mock'] or bool(meta_override.get('derived_from_mock'))
    # Route the override through make_meta so derive is never weaker than the
    # constructor: an out-of-range confidence_score override is dropped by the
    # same validation, not stored raw. derived_from_mock is force-OR'd above, so
    # taint still cannot be cleared (the one law).
    return {'value': value, 'meta': make_meta(**overridden)}
