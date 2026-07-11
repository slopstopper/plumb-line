"""provenance — the provenance/lineage law (single source). Mirror of provenance.mjs."""

# Schema version of the provenance metadata envelope (Principle 7). Declared so
# consumers can pin to a shape; embedding it per-meta and validating against it
# is planned. Mirror of PROVENANCE_VERSION in provenance.mjs.
PROVENANCE_VERSION = 2

STATUS = ['unavailable', 'mock', 'fallback', 'semiReal', 'derived', 'real']
CONFIDENCE = ['none', 'low', 'medium', 'high']

# Deprecated no-op, kept for import compatibility. Step IDs are now assigned by
# a counter local to each combine_provenance call (see below), so there is no
# shared state to reset between runs. Safe to delete from call sites.
def reset_step_counter():
    pass

def is_score(x):
    """Return True when x is a real number in [0, 1] (booleans excluded)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 1


def make_meta(source='derived', confidence='none', confidence_score=None,
              derived_from_mock=None, lineage=None, weakest_source=None,
              basis=None, adapter=None):
    """Construct a provenance metadata dict.

    Args:
        source: One of STATUS. Defaults to ``"derived"``.
        confidence: One of CONFIDENCE. Defaults to ``"none"``.
        confidence_score: Numeric precision in [0, 1]; omitted when invalid.
        derived_from_mock: Defaults to ``source == "mock"``.
        lineage: List of prior lineage step dicts; each step is shallow-copied.
        weakest_source: Lowest-ranked source in ancestry; one of STATUS.
        basis: Arbitrary domain metadata (passed through unchanged).
        adapter: Adapter identifier (passed through unchanged).

    Returns:
        dict: Provenance metadata envelope.
    """
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
        input_steps.append(step)
    # Renumber the *entire* output lineage from a combine-local counter, so step
    # IDs are unique-within-output (SPEC §4) for every input shape — two
    # independently-built inputs each start at step-1, so seeding past the prior
    # length alone wouldn't stop their inherited steps from colliding. No
    # module-level state means concurrent combines can't collide either. IDs are
    # thus a pure function of output structure, not creation order. See #23.
    lineage = [dict(s, id=f"step-{i + 1}") for i, s in enumerate(prior + input_steps)]
    return make_meta(source='derived', confidence=confidence,
                     confidence_score=confidence_score,
                     derived_from_mock=derived_from_mock, lineage=lineage,
                     # Weakest source anywhere in the ancestry, read off the lineage.
                     weakest_source=weakest_source(*[s.get('source') for s in lineage]))
