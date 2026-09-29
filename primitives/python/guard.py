"""guard — the egress guard (#120, ADR-0020).

``audit_meta`` reports a problem after the fact; ``guard`` stops a value at an
output point unless its envelope backs what the output claims. Fail closed: a
value with no envelope, a malformed one, or one the audit flags is refused,
and taint and confidence are judged from the whole lineage, not the headline
fields alone. JS twin: primitives/js/guard.mjs.
"""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import CONFIDENCE, STATUS, taints, weakest_confidence, _json
    from .audit import audit_meta, validate_envelope
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'combine_provenance') or not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    CONFIDENCE, STATUS, taints, weakest_confidence, _json = (
        _prov.CONFIDENCE, _prov.STATUS, _prov.taints, _prov.weakest_confidence, _prov._json)
    from audit import audit_meta, validate_envelope

# The audit's advisories about the version field that do not stop a value: an
# envelope older or newer than this library is judged on what it carries
# (SPEC §5b: a version exists to make drift legible, not to gate). A malformed
# version is not among them.
_ADVISORY = ('version-legacy:', 'version-future:')


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


def _on(ladder, value):
    # `True == 1` and unhashable values: a rung is a str on the ladder, nothing else.
    return isinstance(value, str) and value in ladder


def _unreadable(meta):
    """What the guard cannot read on the ladders is malformed (SPEC §5c). The
    constructors refuse such values (ADR-0019) and the law tolerates them in a
    handed envelope, but an output point fails closed. Field names are the
    canonical camelCase ones, as validate_envelope reports them."""
    issues = []
    if not _on(STATUS, meta['source']):
        issues.append(f"source {_json(meta['source'])} is not on the source ladder")
    if not _on(CONFIDENCE, meta['confidence']):
        issues.append(f"confidence {_json(meta['confidence'])} is not on the confidence ladder")
    if 'weakest_source' in meta and not _on(STATUS, meta['weakest_source']):
        issues.append(f"weakestSource {_json(meta['weakest_source'])} is not on the source ladder")
    for i, step in enumerate(meta['lineage']):
        if not isinstance(step, dict):
            issues.append(f'lineage step {i} is not an object')
            continue
        if 'source' in step and not _on(STATUS, step['source']):
            issues.append(f"lineage step {i} source {_json(step['source'])} is not on the source ladder")
        if 'confidence' in step and not _on(CONFIDENCE, step['confidence']):
            issues.append(f"lineage step {i} confidence {_json(step['confidence'])} is not on the confidence ladder")
        if 'derived_from_mock' in step and not isinstance(step['derived_from_mock'], bool):
            issues.append(f'lineage step {i} derivedFromMock must be a boolean')
    return issues


def guard(x, *, no_mock=True, min_confidence='none', **unknown):
    """Let a marked value through an output point only if its envelope backs it.

    Returns the value it was given, unchanged, so an output point writes
    ``unwrap(guard(x))``; otherwise raises :class:`ProvenanceRefused` listing
    every reason.

    Args:
        x: A marked dict produced by ``mark`` or ``derive``.
        no_mock: Refuse mock taint anywhere in the envelope or its lineage. On
            unless turned off (Principle 4's mock clause: excluded from outputs
            unless explicitly opted in).
        min_confidence: Refuse when the weakest confidence in the envelope or
            its lineage is below this level.

    Returns:
        ``x``.

    Raises:
        ProvenanceRefused: when the value may not leave (a ``ValueError``).
        TypeError: when an option is unknown or has a bad value. Never a
            ``ValueError``, so a catch written for refusals does not swallow a
            bad option.
    """
    # A bad option is the caller's mistake, not the value's: raised before the
    # value is looked at, and never a ProvenanceRefused.
    if unknown:
        # A misspelt option would otherwise leave its check at the default.
        raise TypeError(f"guard: unknown option {', '.join(unknown)}")
    if not isinstance(no_mock, bool):
        raise TypeError(f'guard: the no-mock option must be a boolean; got {_json(no_mock)}')
    if not _on(CONFIDENCE, min_confidence):
        raise TypeError(
            f"guard: the minimum confidence must be one of {', '.join(CONFIDENCE)}; "
            f'got {_json(min_confidence)}')
    # A marked value as mark() and derive() build it: {'value': ..., 'meta': {...}}.
    if not isinstance(x, dict) or 'value' not in x or 'meta' not in x:
        raise ProvenanceRefused(['not a marked value: it carries no provenance envelope'])
    meta = x['meta']
    # A copy, as JS's metaOf makes: an order-preserving parse (a dict
    # subclass, the twin of JS's null-prototype parse) is judged on content.
    if isinstance(meta, dict):
        meta = dict(meta)
    malformed = validate_envelope(meta) or _unreadable(meta)
    if malformed:
        raise ProvenanceRefused([f'invalid envelope: {issue}' for issue in malformed])
    reasons = [f'audit: {issue}' for issue in audit_meta(meta)
               if not issue.startswith(_ADVISORY)]
    steps = meta['lineage']
    if no_mock and (taints(meta) or meta.get('weakest_source') == 'mock'
                    or any(taints(step) for step in steps)):
        reasons.append('mock: the value derives from mock data, and this output does not allow it')
    if min_confidence != 'none':
        # An absent step confidence counts as none: the guard vouches only for
        # what the lineage states.
        weakest = weakest_confidence(meta['confidence'], *(step.get('confidence') for step in steps))
        if CONFIDENCE.index(weakest) < CONFIDENCE.index(min_confidence):
            reasons.append(f'confidence: {weakest} is below the required {min_confidence}')
    if reasons:
        raise ProvenanceRefused(reasons)
    return x
