"""marked — thin wrapper sugar over the provenance law. The law lives in provenance.py."""
from collections.abc import Iterable, Mapping

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
    # The inputs are read once, into a list (#550 review): a generator was
    # otherwise used up by the check and combined as zero inputs, dropping its
    # taint. A string, a mapping or a non-iterable is not a list of inputs.
    if isinstance(inputs, (str, bytes, Mapping)) or not isinstance(inputs, Iterable):
        raise TypeError('derive: inputs must be a list of marked values')
    items = list(inputs)
    # Every input must be a marked value, as the egress guard reads one: a dict
    # holding 'value' and 'meta' (#550). Python raised an unrelated KeyError
    # or TypeError here while the JS twin combined an unmarked object or None
    # as an unknown input; an input with no envelope is kept out at the source.
    # Checked before fn runs.
    for i, item in enumerate(items):
        if not (isinstance(item, dict) and 'value' in item and 'meta' in item):
            raise TypeError(f'derive: input {i} is not a marked value (mark it first)')
    value = fn(*[unwrap(i) for i in items])
    combined = combine_provenance(*[meta_of(i) for i in items])
    overridden = dict(combined)
    # provenance_version is stamped by make_meta itself from the constant; it is
    # not one of make_meta's parameters, so it must not be re-forwarded here.
    overridden.pop('provenance_version', None)
    for key in _OVERRIDE_KEYS:
        if key in meta_override:
            overridden[key] = meta_override[key]
    # A malformed taint override is passed to make_meta as it is, so make_meta
    # refuses it with its own message and quoting (#555): read as taint it was
    # called mock, and it must not be dropped silently.
    flag = meta_override.get('derived_from_mock')
    readable = flag is None or isinstance(flag, bool)
    overridden['derived_from_mock'] = (combined['derived_from_mock'] or flag is True) if readable else flag
    # Route the override through make_meta so derive is never weaker than the
    # constructor: an out-of-range confidence_score override is dropped by the
    # same validation, not stored raw. derived_from_mock is force-OR'd above, so
    # taint still cannot be cleared (the one law).
    return {'value': value, 'meta': make_meta(**overridden)}
