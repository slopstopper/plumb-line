"""provenance — the provenance/lineage law (single source). Mirror of provenance.mjs."""

import hashlib
import json
import struct

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
        basis: Arbitrary domain metadata (passed through unchanged).
        adapter: Adapter identifier (passed through unchanged).

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
    meta = {
        'provenance_version': PROVENANCE_VERSION,
        'source': source,
        'confidence': confidence,
        'derived_from_mock': (source == 'mock') if derived_from_mock is None else bool(derived_from_mock),
        # Each meta owns its own copy of every lineage step (dicts are cloned),
        # so mutating one envelope's history can't rewrite a sibling that shares
        # ancestry. Python has no cheap deep-freeze, so this isolates ownership
        # rather than enforcing the true immutability the JS Object.freeze gives.
        'lineage': [dict(s) if isinstance(s, dict) else s for s in lineage] if isinstance(lineage, list) else [],
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

def taints(meta):
    """Return True when the envelope carries mock taint.

    Taint is present when ``derived_from_mock`` is truthy or ``source`` is ``"mock"``.

    Args:
        meta: Provenance metadata dict, or None.

    Returns:
        bool
    """
    if not meta:
        return False
    return bool(meta.get('derived_from_mock')) or meta.get('source') == 'mock'

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
    return min(scores)

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
    derived_from_mock = any(taints(m) for m in metas)
    confidence = weakest_confidence(*[(m or {}).get('confidence') for m in metas])
    confidence_score = combine_confidence_score([(m or {}).get('confidence_score') for m in metas])
    prior = []
    for m in metas:
        if not m:
            continue
        lin = m.get('lineage')
        if isinstance(lin, list):
            prior.extend(lin)
    # Prior steps keep their content-addressed ids verbatim — a subtree's id must
    # not change because it was recombined (#52). Only new input steps are minted.
    input_steps = []
    for m in metas:
        step = {
            'of': 'input',
            'source': (m or {}).get('source'),
            'confidence': (m or {}).get('confidence'),
            'derived_from_mock': taints(m),
        }
        # Record the numeric score too when the input carries one, so the numeric
        # over-claim audit works on real derive output, not just hand-built metas.
        score = (m or {}).get('confidence_score')
        if is_score(score):
            step['confidence_score'] = score
        prior_ids = [s.get('id') for s in ((m or {}).get('lineage') or []) if isinstance(s.get('id'), str)]
        step['id'] = step_id(step, prior_ids)
        input_steps.append(step)
    lineage = prior + input_steps
    return make_meta(source='derived', confidence=confidence,
                     confidence_score=confidence_score,
                     derived_from_mock=derived_from_mock, lineage=lineage,
                     # Weakest source anywhere in the ancestry, read off the lineage.
                     weakest_source=weakest_source(*[s.get('source') for s in lineage]))


def step_id(step, input_ids=None):
    """Content-addressed id for a lineage step (#52). Mirror of stepId in provenance.mjs."""
    input_ids = input_ids or []
    score = step.get('confidence_score')
    # Canonical score encoding: IEEE-754 big-endian 8-byte representation as
    # lowercase hex. json.dumps/JSON.stringify disagree across languages for
    # small floats (e.g. 0.00001: Python "1e-05" vs JS "0.00001"), which would
    # otherwise produce different step ids for the same value cross-language.
    # The raw double bit pattern is identical in both, by construction.
    score_s = struct.pack('>d', score).hex() if is_score(score) else '-'
    of_ = '' if step.get('of') is None else step.get('of')
    source_ = '' if step.get('source') is None else step.get('source')
    confidence_ = '' if step.get('confidence') is None else step.get('confidence')
    canon = "\n".join([
        f"of={of_}",
        f"source={source_}",
        f"confidence={confidence_}",
        f"derivedFromMock={'true' if step.get('derived_from_mock') else 'false'}",
        f"confidenceScore={score_s}",
        f"inputs={','.join(sorted(input_ids))}",
    ])
    return 'sha256:' + hashlib.sha256(canon.encode()).hexdigest()[:12]
