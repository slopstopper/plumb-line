"""audit — runtime consistency checker for provenance metadata. Mirror of audit.mjs."""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import CONFIDENCE, STATUS, weakest_confidence, weakest_source, is_score
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from provenance import CONFIDENCE, STATUS, weakest_confidence, weakest_source, is_score

CLEAN_SOURCES = ['real', 'semiReal', 'fallback']

def audit_meta(meta):
    if meta is None:
        return ['missing meta']
    issues = []
    lineage = meta.get('lineage') if isinstance(meta.get('lineage'), list) else []
    # Per-step field reads use this dict-only view so a malformed step (None, a
    # bare string) reads as "no signal" instead of raising — mirroring the JS
    # `s?.field`. The raw `lineage` is kept for the length check below, exactly as
    # JS counts `lineage.length`, so audit stays total (never throws). (G3)
    steps = [s for s in lineage if isinstance(s, dict)]

    if meta.get('source') in CLEAN_SOURCES and meta.get('derived_from_mock') is True:
        issues.append(f"laundering: clean source '{meta.get('source')}' but derived_from_mock is true")

    # An unknown confidence on a step is laundering, not "no signal": treat it as
    # the 'none' floor (mirroring weakest_confidence), so audit is never laxer than
    # the combination law. A step that records *no* confidence is still skipped —
    # absence is genuinely unrankable and must not manufacture a false over-claim.
    lineage_confidences = [
        c if c in CONFIDENCE else 'none'
        for c in (s.get('confidence') for s in steps)
        if c is not None
    ]
    if lineage_confidences:
        weakest = weakest_confidence(*lineage_confidences)
        c = meta.get('confidence')
        top_idx = CONFIDENCE.index(c) if c in CONFIDENCE else -1
        if top_idx > CONFIDENCE.index(weakest):
            issues.append(f"over-claiming: confidence '{c}' exceeds weakest lineage confidence '{weakest}'")

    # Numeric over-claiming — the higher-resolution analog of the ordinal check.
    if is_score(meta.get('confidence_score')):
        lineage_scores = [s.get('confidence_score') for s in steps if is_score(s.get('confidence_score'))]
        if lineage_scores:
            weakest = min(lineage_scores)
            if meta['confidence_score'] > weakest:
                issues.append(f"over-claiming: confidenceScore {meta['confidence_score']} exceeds weakest lineage score {weakest}")

    # Source over-claim — weakest_source cannot look cleaner than the lineage proves.
    if meta.get('weakest_source') in STATUS:
        actual = weakest_source(*[s.get('source') for s in steps])
        if actual is not None and STATUS.index(meta['weakest_source']) > STATUS.index(actual):
            issues.append(f"source over-claim: weakestSource '{meta['weakest_source']}' is cleaner than lineage's '{actual}'")

    lineage_tainted = any(bool(s.get('derived_from_mock')) or s.get('source') == 'mock' for s in steps)
    if lineage_tainted and meta.get('derived_from_mock') is False:
        issues.append('taint dropped: lineage contains a tainted step but derived_from_mock is false')

    if meta.get('source') == 'derived' and len(lineage) == 0:
        issues.append('unreproducible: derived value has no lineage')

    return issues


# The four required fields (SPEC §1) and their type predicates. Keys are the
# Python (snake_case) envelope keys; the label is the canonical camelCase name
# used in messages so conformance needles match JS verbatim (parity is the data
# contract, not a prose promise).
_REQUIRED_FIELDS = [
    ('source', lambda v: isinstance(v, str), 'a string'),
    ('confidence', lambda v: isinstance(v, str), 'a string'),
    ('derived_from_mock', lambda v: isinstance(v, bool), 'a boolean'),
    ('lineage', lambda v: isinstance(v, list), 'an array'),
]
_FIELD_LABEL = {'derived_from_mock': 'derivedFromMock'}


def validate_envelope(meta):
    """The *structural* checker, complementary to audit_meta. Mirror of
    validateEnvelope in audit.mjs.

    audit_meta verifies logical consistency among the fields that ARE present
    and tolerates absence as "unknown" (SPEC §2); it therefore passes a
    structurally empty ``{}``. validate_envelope verifies the four required
    fields (SPEC §1) are present and well-typed. Like audit_meta it is total: it
    returns a list of issue strings (empty = structurally valid), never raises.
    """
    if meta is None:
        return ['missing meta']
    if not isinstance(meta, dict):
        return ['not an envelope object']
    issues = []
    for key, ok, type_label in _REQUIRED_FIELDS:
        label = _FIELD_LABEL.get(key, key)
        if key not in meta:
            issues.append(f'missing required field: {label}')
        elif not ok(meta[key]):
            issues.append(f"field '{label}' must be {type_label}")
    return issues
