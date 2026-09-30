"""guard — the egress guard (#120, ADR-0020).

``audit_meta`` reports a problem after the fact; ``guard`` stops a value at an
output point unless its envelope backs what the output claims. Fail closed: a
value with no envelope, a malformed one, or one the audit flags is refused,
and taint and confidence are judged from the whole lineage, not the headline
fields alone. JS twin: primitives/js/guard.mjs.
"""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import CONFIDENCE, STATUS, is_score, taints, weakest_confidence, _json
    from .audit import audit_meta, validate_envelope
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'combine_provenance') or not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    CONFIDENCE, STATUS, is_score, taints, weakest_confidence, _json = (
        _prov.CONFIDENCE, _prov.STATUS, _prov.is_score, _prov.taints, _prov.weakest_confidence, _prov._json)
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
    ``confidence:``, ``source:``); the message joins them after ``provenance refused: ``,
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
    constructors refuse an off-ladder source or confidence (ADR-0019) and drop
    an invalid score; the law tolerates all of these in a handed envelope, and
    an output point fails closed. Field names are the canonical camelCase ones,
    as validate_envelope reports them."""
    issues = []
    if not _on(STATUS, meta['source']):
        issues.append(f"source {_json(meta['source'])} is not on the source ladder")
    if not _on(CONFIDENCE, meta['confidence']):
        issues.append(f"confidence {_json(meta['confidence'])} is not on the confidence ladder")
    if 'weakest_source' in meta and not _on(STATUS, meta['weakest_source']):
        issues.append(f"weakestSource {_json(meta['weakest_source'])} is not on the source ladder")
    if 'confidence_score' in meta and not is_score(meta['confidence_score']):
        issues.append(f"confidenceScore {_json(meta['confidence_score'])} is not a number in [0, 1]")
    for i, step in enumerate(meta['lineage']):
        if not isinstance(step, dict):
            issues.append(f'lineage step {i} is not a plain object')
            continue
        # A step with no source is refused (#525 review): a missing
        # confidence counts as none, the weakest rung, but a source has no
        # rung the guard could degrade it to and still judge, so it cannot be
        # shown not to be mock. Combine always writes a source, None when its
        # input had none.
        if 'source' not in step:
            issues.append(f'lineage step {i} has no source')
        elif not _on(STATUS, step['source']):
            issues.append(f"lineage step {i} source {_json(step['source'])} is not on the source ladder")
        if 'confidence' in step and not _on(CONFIDENCE, step['confidence']):
            issues.append(f"lineage step {i} confidence {_json(step['confidence'])} is not on the confidence ladder")
        if 'derived_from_mock' in step and not isinstance(step['derived_from_mock'], bool):
            issues.append(f'lineage step {i} derivedFromMock must be a boolean')
        # The audit skips a score it cannot read, so a bad one could hide an
        # over-claim against a readable top-level score.
        if 'confidence_score' in step and not is_score(step['confidence_score']):
            issues.append(f"lineage step {i} confidenceScore {_json(step['confidence_score'])} is not a number in [0, 1]")
    return issues


def guard(x, *, no_mock=True, min_confidence='none', min_source='unavailable', **unknown):
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
        min_source: Refuse when the weakest source the ancestry shows (the
            headline, weakest_source and every lineage step, skipping the
            law's own label 'derived') is below this rung. Off by default,
            by the owner's decision (#541): refuses fallback and inferred
            data without a mock label; assumes a complete lineage.

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
    if not _on(STATUS, min_source):
        raise TypeError(
            f"guard: the minimum source must be one of {', '.join(STATUS)}; "
            f'got {_json(min_source)}')
    # A marked value as mark() and derive() build it: {'value': ..., 'meta': {...}}.
    if not isinstance(x, dict) or 'value' not in x or 'meta' not in x:
        raise ProvenanceRefused(['not a marked value: it carries no provenance envelope'])
    meta = x['meta']
    # A copy, as JS's metaOf makes: an order-preserving parse (a dict
    # subclass, the twin of JS's null-prototype parse) is judged on content.
    # dict.items reads the dict's own storage, so a subclass whose accessors or
    # iteration hide a field (or raise) is judged on what it holds, not on
    # what it answers. Each step is copied the same way.
    if isinstance(meta, dict):
        meta = dict(dict.items(meta))
        if isinstance(meta.get('lineage'), list):
            meta['lineage'] = [dict(dict.items(step)) if isinstance(step, dict) else step
                               for step in meta['lineage']]
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
    if min_source != STATUS[0]:
        # The rest of Principle 4 beside its mock clause (#541): the weakest
        # source the ancestry shows, from the headline, weakest_source and
        # every step. 'derived' is the law's own label for a computed value,
        # not a source of data, so it is skipped. Every step here has a source
        # on the ladder (a step without one was refused above as invalid).
        sources = [src for src in (meta.get('source'), meta.get('weakest_source'),
                                   *(step.get('source') for step in steps))
                   if _on(STATUS, src) and src != 'derived']
        if not sources:
            reasons.append(f'source: no source in the ancestry shows it meets the required {min_source}')
        else:
            weakest_src = min(sources, key=STATUS.index)
            if STATUS.index(weakest_src) < STATUS.index(min_source):
                reasons.append(f'source: {weakest_src} is below the required {min_source}')
    if reasons:
        raise ProvenanceRefused(reasons)
    return x
