"""provenance — the provenance/lineage law (single source). Mirror of provenance.mjs."""

import hashlib
import json
import math
import re
import struct
from collections.abc import Mapping

# Schema version of the provenance metadata envelope (Principle 7). Declared so
# consumers can pin to a shape; every envelope now carries this constant
# (embedded by make_meta and validated on read). Mirror of
# PROVENANCE_VERSION in provenance.mjs.
PROVENANCE_VERSION = 2

STATUS = ['unavailable', 'mock', 'inferred', 'fallback', 'semiReal', 'derived', 'real']
CONFIDENCE = ['none', 'low', 'medium', 'high']

# Deprecated no-op, kept for import compatibility. Step IDs are now
# content-addressed (see step_id, #52) — there is no counter or other shared
# state to reset between runs. Safe to delete from call sites.
def reset_step_counter():
    pass

def is_score(x):
    """Return True when x is a real number in [0, 1] (booleans excluded)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 1


def _in_ladder(value, ladder):
    """True when value is one of the ladder's strings. Strings only: a value
    equal to a rung but of another type (there is none today) is not one."""
    return isinstance(value, str) and value in ladder


def _json(value):
    """The refused value as a message fragment: JSON where it can be, repr
    otherwise. The JS twin (quote) agrees on the message prefix; the quoted
    value can differ in form (floats, non-ASCII text, containers)."""
    try:
        return json.dumps(value)
    except Exception:  # not JSON: a set, a cycle, too deep, a raising default
        pass
    try:
        return repr(value)
    except Exception:  # a __repr__ that raises must not replace the refusal
        # A constant: even a type name can raise (a hostile metaclass). As JS.
        return '<unprintable>'


class _Required:
    """The default of an argument that has none (#177). A sentinel rather than
    a bare required parameter, so that omitting ``source`` raises the same
    ValueError, with the same message, as the JS twin's missing source."""

    def __repr__(self):
        return '<required>'

    # Checked by identity, so every copy is the one instance.
    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return '_REQUIRED'


_REQUIRED = _Required()


def make_meta(source=_REQUIRED, confidence='none', confidence_score=None,
              derived_from_mock=None, lineage=None, weakest_source=None,
              basis=None, adapter=None):
    """Construct a provenance metadata dict.

    Args:
        source: One of STATUS. Required, with no default (#177): a leaf has
            no parents, so it must say where it came from.
        confidence: One of CONFIDENCE. Defaults to ``"none"``.
        confidence_score: Numeric precision in [0, 1]; omitted when invalid.
        derived_from_mock: Defaults to ``source == "mock"``.
        lineage: List of prior lineage step dicts; each step is shallow-copied.
        weakest_source: Lowest-ranked source in ancestry; one of STATUS.
        basis: Arbitrary domain metadata (passed through unchanged; None
            writes no field, SPEC §1).
        adapter: Adapter identifier (passed through unchanged; None writes no
            field).

    Returns:
        dict: Provenance metadata envelope.

    Raises:
        ValueError: source is missing ("source is required", #177), source is
            not in STATUS, or confidence is not in CONFIDENCE.
    """
    # An out-of-vocabulary rung or source is refused here, not flagged later
    # (#443, owner decision 2026-09-28; ADR-0019): stored, it passed audit_meta
    # silently and the law quietly read it as the weakest rung (SPEC §2). JS
    # twin: makeMeta; the message prefix is the same in both (cases.json
    # "construct"). None is refused, not defaulted, matching JS null. A missing
    # source has no default either (#177, owner decision 2026-09-28): the old
    # "derived" was untrue of a leaf, which has no parents, and audited as
    # unreproducible. confidence still defaults to "none" when omitted.
    if source is _REQUIRED:
        raise ValueError(f"source is required (one of {', '.join(STATUS)})")
    if not _in_ladder(source, STATUS):
        raise ValueError(f"source must be one of {', '.join(STATUS)}; got {_json(source)}")
    if not _in_ladder(confidence, CONFIDENCE):
        raise ValueError(f"confidence must be one of {', '.join(CONFIDENCE)}; got {_json(confidence)}")
    # A taint flag that is not a boolean is refused, as an off-ladder rung is
    # (#555, ADR-0019 amendment): read as taint it called an unreadable value
    # mock. None takes the default.
    if not _is_taint_flag(derived_from_mock):
        raise ValueError(f"derivedFromMock must be a boolean; got {_json(derived_from_mock)}")
    meta = {
        'provenance_version': PROVENANCE_VERSION,
        'source': source,
        'confidence': confidence,
        'derived_from_mock': (source == 'mock') if derived_from_mock is None else derived_from_mock,
        # Each meta owns its own copy of every lineage step (dicts are cloned),
        # so mutating one envelope's history can't rewrite a sibling that shares
        # ancestry. Python has no cheap deep-freeze, so this isolates ownership
        # rather than enforcing the true immutability the JS Object.freeze gives.
        # A list step is copied as a list, as the JS twin copies an array, and
        # any Mapping step as a dict (#525).
        'lineage': [dict(s) if isinstance(s, Mapping) else list(s) if isinstance(s, list) else s
                    for s in lineage] if isinstance(lineage, list) else [],
    }
    # Optional numeric confidence — a finer-grained companion to the ordinal
    # `confidence`, never a replacement. Stored only when it is a valid score.
    if is_score(confidence_score):
        meta['confidence_score'] = confidence_score
    # Computed-only resolution beyond the derived_from_mock boolean; passed
    # through so chained derives carry it, never settable as a derive override.
    if weakest_source in STATUS:
        meta['weakest_source'] = weakest_source
    if basis is not None:
        meta['basis'] = basis
    if adapter is not None:
        meta['adapter'] = adapter
    return meta

def weakest_confidence(*levels):
    """Return the weakest (lowest-ranked) confidence level among the given values.

    Unknown values are treated as ``"none"``. Returns ``"none"`` with no arguments.

    Args:
        *levels: Values from CONFIDENCE.

    Returns:
        str: Weakest confidence level.
    """
    if not levels:
        return 'none'
    min_idx = len(CONFIDENCE) - 1
    for level in levels:
        idx = CONFIDENCE.index(level) if level in CONFIDENCE else 0
        min_idx = min(min_idx, idx)
    return CONFIDENCE[min_idx]

def _is_taint_flag(value):
    """Whether a ``derived_from_mock`` value is one the law can read: a bool,
    or absent (None). Anything else is malformed (#555): not taint, since
    nothing shows it means mock, and not clean either. The constructors refuse
    it and combine keeps it on its step as it is, so the egress guard refuses
    it as invalid. JS twin: isTaintFlag."""
    return value is None or isinstance(value, bool)


def _ranked(source):
    """True when `source` is on the status ladder. Membership is tested by
    string, so an unhashable or odd value is simply not ranked."""
    return isinstance(source, str) and source in STATUS


def _field(meta, key):
    """``meta[key]`` for an envelope, else None: an input that is not an
    envelope carries no fields, as in the JS twin, where ``m?.key`` is
    undefined for a string or a number (#525). Any Mapping is an envelope,
    not only a dict: read as carrying nothing, a MappingProxyType or UserDict
    had its taint cleared (#525 review)."""
    return meta.get(key) if isinstance(meta, Mapping) else None


def taints(meta):
    """Return True when the envelope carries mock taint.

    Taint is present when ``derived_from_mock`` is True or ``source`` is
    ``"mock"`` (SPEC §3). Only a bool True taints: a malformed flag is not
    read as mock (#555, reversing #525).

    Args:
        meta: Provenance metadata dict, or any other value (which carries no
            taint of its own).

    Returns:
        bool
    """
    return _field(meta, 'derived_from_mock') is True or _field(meta, 'source') == 'mock'

def weakest_source(*sources):
    """Return the least-trustworthy source by STATUS rank.

    Unknown values are ignored. Returns ``None`` when nothing is rankable.

    Args:
        *sources: Values from STATUS.

    Returns:
        str | None: Weakest STATUS value, or None.
    """
    min_idx = len(STATUS)
    for s in sources:
        if s in STATUS:
            min_idx = min(min_idx, STATUS.index(s))
    return None if min_idx == len(STATUS) else STATUS[min_idx]

def combine_confidence_score(scores):
    """Return the minimum numeric confidence score, but only when every element is valid.

    Returns ``None`` if any element is missing or invalid — a gap is "unknown", not zero.

    Args:
        scores: List of candidate confidence scores.

    Returns:
        float | None
    """
    if not scores or not all(is_score(s) for s in scores):
        return None
    # -0.0 is returned as 0.0: min() over 0.0 and -0.0 returns whichever came
    # first, so the result depended on input order (#525 review). abs() keeps
    # an int 0 an int.
    low = min(scores)
    return abs(low) if low == 0 else low

def combine_provenance(*metas):
    """Apply the taint-propagation combination law to one or more metadata dicts.

    Mock taint propagates forward and cannot be cleared. Calling with zero
    arguments returns an ``"unavailable"`` envelope (not ``"derived"``), because
    a value derived from nothing has no honest provenance.

    Args:
        *metas: Provenance dicts produced by :func:`make_meta`.

    Returns:
        dict: Combined envelope with ``source: "derived"``.
    """
    # A value combined from no inputs is derived from nothing — honestly
    # 'unavailable', not 'derived'. Returning 'derived' with an empty lineage
    # would contradict audit_meta's "derived value has no lineage" check
    # (SPEC §3 vs §5). See #25.
    if not metas:
        return make_meta(source='unavailable', confidence='none',
                         derived_from_mock=False, lineage=[])
    # Total over any input, as the JS twin is (#525): a value that is not an
    # envelope, a lineage that is not a list and a step that is not a dict are
    # read as carrying nothing, never an AttributeError.
    derived_from_mock = any(taints(m) for m in metas)
    confidence = weakest_confidence(*[_field(m, 'confidence') for m in metas])
    confidence_score = combine_confidence_score([_field(m, 'confidence_score') for m in metas])

    def lineage_of(m):
        lin = _field(m, 'lineage')
        return lin if isinstance(lin, list) else []
    prior = []
    for m in metas:
        prior.extend(lineage_of(m))
    # Prior steps keep their content-addressed ids verbatim — a subtree's id must
    # not change because it was recombined (#52). Only new input steps are minted.
    input_steps = []
    for m in metas:
        # The input's source and confidence, None when it has none, as for an
        # input that is not an envelope (#525). A step always has both keys:
        # the guard refuses a step without them (#525 review).
        step = {
            'of': 'input',
            'source': _field(m, 'source'),
            'confidence': _field(m, 'confidence'),
            # A malformed taint flag is kept as the input carries it, neither
            # read as taint nor cleaned, so the guard refuses the step (#555).
            'derived_from_mock': (taints(m) if _is_taint_flag(_field(m, 'derived_from_mock'))
                                  else _field(m, 'derived_from_mock')),
        }
        # Record the numeric score too when the input carries one, so the numeric
        # over-claim audit works on real derive output, not just hand-built metas.
        score = _field(m, 'confidence_score')
        if is_score(score):
            step['confidence_score'] = score
        prior_ids = [s['id'] for s in lineage_of(m) if isinstance(s, Mapping) and isinstance(s.get('id'), str)]
        step['id'] = step_id(step, prior_ids)
        input_steps.append(step)
    lineage = prior + input_steps
    sources = [_field(s, 'source') for s in lineage]
    return make_meta(source='derived', confidence=confidence,
                     confidence_score=confidence_score,
                     derived_from_mock=derived_from_mock, lineage=lineage,
                     # Weakest source anywhere in the ancestry, read off the lineage,
                     # and omitted when any step's source cannot be ranked (#551):
                     # read off the known steps alone, an unknown ancestor left the
                     # result looking clean.
                     weakest_source=(weakest_source(*sources)
                                     if all(_ranked(src) for src in sources) else None))


def _double_hex(v):
    """A number as its IEEE-754 binary64 bit pattern, 16 lowercase hex chars.
    An int too large for a double is +/-infinity, as JSON.parse reads it
    (math.copysign would itself overflow), and -0.0 is written as 0.0, since
    JSON's -0 is -0 in JS and the int 0 here (#525 review). JS twin:
    doubleHex."""
    try:
        f = float(v)
    except OverflowError:
        f = math.inf if v > 0 else -math.inf
    return struct.pack('>d', 0.0 if f == 0 else f).hex()


def _canon_field(v):
    """One ``of`` / ``source`` / ``confidence`` value as the step-id canon
    writes it (SPEC §4, #525). A string is itself and an absent value is
    empty, as always; any other value a handed envelope can carry is written
    by type, the same in both languages: a boolean as true/false, a number as
    its IEEE-754 bit pattern (so 1 and 1.0 agree; an int too large for a
    double is +/-infinity, as JSON.parse reads it), a list or dict as
    <array> / <object>. JS twin: canonField."""
    if v is None:
        return ''
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return _double_hex(v)
    return '<array>' if isinstance(v, (list, tuple)) else '<object>'


def _flag_canon(v):
    """The step-id canon's derivedFromMock line: a bool as true/false, absent
    as false, and a malformed flag (kept by combine, #555) by type, so an
    empty string is empty, not false. JS twin: the derivedFromMock line in
    stepId."""
    return 'false' if v is None else _canon_field(v)


def step_id(step, input_ids=None):
    """Content-addressed id for a lineage step (#52). Mirror of stepId in provenance.mjs."""
    input_ids = input_ids or []
    score = _field(step, 'confidence_score')
    # Canonical score encoding: IEEE-754 big-endian 8-byte representation as
    # lowercase hex. json.dumps/JSON.stringify disagree across languages for
    # small floats (e.g. 0.00001: Python "1e-05" vs JS "0.00001"), which would
    # otherwise produce different step ids for the same value cross-language.
    # The raw double bit pattern is identical in both, by construction.
    score_s = _double_hex(score) if is_score(score) else '-'
    canon = "\n".join([
        f"of={_canon_field(_field(step, 'of'))}",
        f"source={_canon_field(_field(step, 'source'))}",
        f"confidence={_canon_field(_field(step, 'confidence'))}",
        # A bool as true/false, absent as false, and a malformed flag (kept by
        # combine, #555) by type, as the fields above are.
        f"derivedFromMock={_flag_canon(_field(step, 'derived_from_mock'))}",
        f"confidenceScore={score_s}",
        f"inputs={','.join(sorted(input_ids))}",
    ])
    # A lone surrogate (JSON can carry one) is hashed as U+FFFD, as Node's
    # UTF-8 encoder writes it; str.encode() raised (#525 review).
    canon = re.sub('[\ud800-\udfff]', '\ufffd', canon)
    return 'sha256:' + hashlib.sha256(canon.encode()).hexdigest()[:12]
