"""audit — runtime consistency checker for provenance metadata. Mirror of audit.mjs."""
import math
import sys

_FLOAT_MAX = sys.float_info.max

# Sentinel distinguishing an ABSENT key from an explicit null. dict.get() collapses
# both to None; JS sees `undefined` vs `null` natively. That asymmetry is what made
# the two checkers disagree on an explicit null version (#156).
_MISSING = object()

try:  # installed as a package (plumb_line_provenance)
    from .provenance import CONFIDENCE, STATUS, weakest_confidence, weakest_source, is_score, PROVENANCE_VERSION
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    import provenance as _prov
    if not hasattr(_prov, 'combine_provenance') or not hasattr(_prov, 'PROVENANCE_VERSION'):
        raise ImportError(
            "a foreign 'provenance' module shadowed plumb-line's primitive "
            f"(loaded from {getattr(_prov, '__file__', '?')}); rename it or use the "
            "installed 'plumb_line_provenance' package"
        )
    CONFIDENCE, STATUS = _prov.CONFIDENCE, _prov.STATUS
    weakest_confidence, weakest_source = _prov.weakest_confidence, _prov.weakest_source
    is_score, PROVENANCE_VERSION = _prov.is_score, _prov.PROVENANCE_VERSION

CLEAN_SOURCES = ['real', 'semiReal', 'fallback']

def audit_meta(meta):
    """Check a provenance metadata dict for internal consistency.

    Returns an empty list when the envelope is consistent; otherwise returns
    one string per issue. Issue prefixes:

    - ``"laundering:"`` — a clean source combined with mock taint
    - ``"over-claiming:"`` — confidence or confidence_score higher than lineage supports
    - ``"source over-claim:"`` — weakest_source cleaner than lineage proves
    - ``"taint dropped:"`` — a tainted lineage step but derived_from_mock is False
    - ``"unreproducible:"`` — source is ``"derived"`` but lineage is empty
    - ``"missing meta"`` — meta is None or not a dict
    - ``"version-legacy:"`` — envelope predates the current provenance version, or omits it
    - ``"version-future:"`` — envelope reports a newer version than this checker supports
    - ``"version-malformed:"`` — the version field is present but is not a finite
      number (#156). A fractional version is finite, so it is compared like any
      other, not rejected — the branch is about finiteness, not integer-ness.

    Args:
        meta: Provenance metadata dict to audit, or None.

    Returns:
        list[str]: Issue descriptions; empty means consistent.
    """
    # Exact dict, not isinstance (#165). JS auditMeta rejects any non-plain object
    # via `Object.getPrototypeOf(meta) !== Object.prototype`, so accepting dict
    # SUBCLASSES here (OrderedDict, defaultdict) would diverge — and parity is the
    # invariant this project sells. Deliberately stricter than validate_envelope
    # below, which mirrors the looser JS validateEnvelope.
    if type(meta) is not dict:
        return ['missing meta']
    issues = []

    # Version read policy (#93): forgiving forward, honest backward. Advisory only.
    # Absent is legacy (an envelope predating the field). Present-but-not-a-number
    # is malformed, NOT legacy (#156) — saying "predates version N" about a list or
    # a bool asserts something false. `_MISSING` distinguishes an absent key from an
    # explicit null: .get() collapses both to None, which is what made JS and Python
    # diverge here (JS saw `undefined` vs `null` and treated only the former as
    # legacy). bool is excluded explicitly because it IS an int subclass in Python.
    v = meta.get('provenance_version', _MISSING)
    if v is _MISSING:
        issues.append(f'version-legacy: envelope predates version {PROVENANCE_VERSION}')
    elif (not isinstance(v, (int, float)) or isinstance(v, bool)
          or (isinstance(v, float) and not math.isfinite(v))
          or (isinstance(v, int) and abs(v) > _FLOAT_MAX)):
        # isfinite is applied ONLY to floats: math.isfinite(huge_int) converts to
        # float first and raises OverflowError, which would break SPEC §5's
        # totality guarantee (the checker must never raise). Python ints are
        # unbounded, so a version literal past IEEE754 range is also ruled
        # malformed to keep parity — JSON.parse turns the same literal into
        # Infinity in JS, which lands in this branch there.
        issues.append('version-malformed: provenance version is not a finite number')
    elif v < PROVENANCE_VERSION:
        issues.append(f'version-legacy: envelope predates version {PROVENANCE_VERSION}')
    elif v > PROVENANCE_VERSION:
        issues.append(f'version-future: envelope version {v} is newer than supported {PROVENANCE_VERSION}')

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
    structurally empty ``{}`` except for the version-legacy advisory (#93),
    since ``{}`` omits provenance_version. validate_envelope verifies the four required
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
