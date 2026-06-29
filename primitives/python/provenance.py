"""provenance — the provenance/lineage law (single source). Mirror of provenance.mjs."""

# Schema version of the provenance metadata envelope (Principle 7). Declared so
# consumers can pin to a shape; embedding it per-meta and validating against it
# is planned. Mirror of PROVENANCE_VERSION in provenance.mjs.
PROVENANCE_VERSION = 1

STATUS = ['unavailable', 'mock', 'fallback', 'semiReal', 'derived', 'real']
CONFIDENCE = ['none', 'low', 'medium', 'high']

_step_counter = 0

def reset_step_counter():
    global _step_counter
    _step_counter = 0

def _next_step_id():
    global _step_counter
    _step_counter += 1
    return f"step-{_step_counter}"

def is_score(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 1


def make_meta(source='derived', confidence='none', confidence_score=None,
              derived_from_mock=None, lineage=None, weakest_source=None,
              basis=None, adapter=None):
    meta = {
        'source': source,
        'confidence': confidence,
        'derived_from_mock': (source == 'mock') if derived_from_mock is None else bool(derived_from_mock),
        'lineage': list(lineage) if isinstance(lineage, list) else [],
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
    if not levels:
        return 'none'
    min_idx = len(CONFIDENCE) - 1
    for level in levels:
        idx = CONFIDENCE.index(level) if level in CONFIDENCE else 0
        min_idx = min(min_idx, idx)
    return CONFIDENCE[min_idx]

def taints(meta):
    if not meta:
        return False
    return bool(meta.get('derived_from_mock')) or meta.get('source') == 'mock'

def weakest_source(*sources):
    """Least-trustworthy source by STATUS rank; unknowns ignored; None if none rankable."""
    min_idx = len(STATUS)
    for s in sources:
        if s in STATUS:
            min_idx = min(min_idx, STATUS.index(s))
    return None if min_idx == len(STATUS) else STATUS[min_idx]

def combine_confidence_score(scores):
    """Conservative numeric floor: min, but only when every input carries a score."""
    if not scores or not all(is_score(s) for s in scores):
        return None
    return min(scores)

def combine_provenance(*metas):
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
            'id': _next_step_id(),
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
    lineage = prior + input_steps
    return make_meta(source='derived', confidence=confidence,
                     confidence_score=confidence_score,
                     derived_from_mock=derived_from_mock, lineage=lineage,
                     # Weakest source anywhere in the ancestry, read off the lineage.
                     weakest_source=weakest_source(*[s.get('source') for s in lineage]))
