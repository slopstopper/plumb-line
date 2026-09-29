"""guard — the egress guard (#120, ADR-0020).

``audit_meta`` reports a problem after the fact; ``guard`` stops a value at an
output point unless its envelope backs what the output claims. Fail closed: a
value with no envelope, a malformed one, or one the audit flags is refused,
and taint and confidence are judged from the whole lineage, not the headline
fields alone. JS twin: primitives/js/guard.mjs.
"""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import CONFIDENCE, taints, weakest_confidence, _json
    from .audit import audit_meta, validate_envelope
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'combine_provenance') or not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    CONFIDENCE, taints, weakest_confidence, _json = (
        _prov.CONFIDENCE, _prov.taints, _prov.weakest_confidence, _prov._json)
    from audit import audit_meta, validate_envelope


class ProvenanceRefused(ValueError):
    """Raised by :func:`guard` when a value may not leave through an output point.

    ``reasons`` lists every reason, each prefixed with its class (``not a
    marked value``, ``invalid envelope:``, ``audit:``, ``mock:``,
    ``confidence:``); the message joins them after ``provenance refused: ``,
    the same in both languages.
    """

    def __init__(self, reasons):
        self.reasons = list(reasons)
        super().__init__('provenance refused: ' + '; '.join(self.reasons))


def _step_confidence(step):
    return step.get('confidence') if isinstance(step, dict) else None


def guard(x, *, no_mock=True, min_confidence='none'):
    """Let a marked value through an output point only if its envelope backs it.

    Returns the value it was given, unchanged, so an output point writes
    ``unwrap(guard(x))``; otherwise raises :class:`ProvenanceRefused` listing
    every reason.

    Args:
        x: A marked dict produced by ``mark`` or ``derive``.
        no_mock: Refuse mock taint anywhere in the envelope or its lineage. On
            unless turned off (P4: excluded from outputs unless explicitly
            opted in).
        min_confidence: Refuse when the weakest confidence in the envelope or
            its lineage is below this level.

    Returns:
        ``x``.

    Raises:
        ProvenanceRefused: when the value may not leave.
        TypeError: when ``no_mock`` is not a bool (an unknown keyword is a
            TypeError from Python itself).
        ValueError: when ``min_confidence`` is off the ladder.
    """
    # A bad option is the caller's mistake, not the value's: raised before the
    # value is looked at, and never a ProvenanceRefused.
    if not isinstance(no_mock, bool):
        raise TypeError(f'guard: the no-mock option must be a boolean; got {_json(no_mock)}')
    if not isinstance(min_confidence, str) or min_confidence not in CONFIDENCE:
        raise ValueError(
            f"guard: the minimum confidence must be one of {', '.join(CONFIDENCE)}; "
            f'got {_json(min_confidence)}')
    # A marked value as mark() and derive() build it: {'value': ..., 'meta': {...}}.
    if not isinstance(x, dict) or 'value' not in x or 'meta' not in x:
        raise ProvenanceRefused(['not a marked value: it carries no provenance envelope'])
    meta = x['meta']
    invalid = validate_envelope(meta)
    if invalid:
        raise ProvenanceRefused([f'invalid envelope: {issue}' for issue in invalid])
    # The version-legacy advisory is not a refusal: an envelope without a
    # version field is still judged on what it carries (SPEC §5b).
    reasons = [f'audit: {issue}' for issue in audit_meta(meta)
               if not issue.startswith('version-legacy:')]
    steps = meta['lineage']
    if no_mock and (taints(meta) or meta.get('weakest_source') == 'mock'
                    or any(isinstance(step, dict) and taints(step) for step in steps)):
        reasons.append('mock: the value derives from mock data, and this output does not allow it')
    if min_confidence != 'none':
        weakest = weakest_confidence(meta.get('confidence'), *(_step_confidence(s) for s in steps))
        if CONFIDENCE.index(weakest) < CONFIDENCE.index(min_confidence):
            reasons.append(f'confidence: {weakest} is below the required {min_confidence}')
    if reasons:
        raise ProvenanceRefused(reasons)
    return x
