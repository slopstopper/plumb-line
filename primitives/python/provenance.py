"""provenance — the provenance/lineage law (single source). Mirror of provenance.mjs."""

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

def make_meta(source='derived', confidence='none', derived_from_mock=None, lineage=None, basis=None, adapter=None):
    meta = {
        'source': source,
        'confidence': confidence,
        'derived_from_mock': (source == 'mock') if derived_from_mock is None else bool(derived_from_mock),
        'lineage': list(lineage) if isinstance(lineage, list) else [],
    }
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

def combine_provenance(*metas):
    derived_from_mock = any(taints(m) for m in metas)
    confidence = weakest_confidence(*[(m or {}).get('confidence') for m in metas])
    prior = []
    for m in metas:
        if not m:
            continue
        lin = m.get('lineage')
        if isinstance(lin, list):
            prior.extend(lin)
    input_steps = [{
        'id': _next_step_id(),
        'of': 'input',
        'source': (m or {}).get('source'),
        'confidence': (m or {}).get('confidence'),
        'derived_from_mock': taints(m),
    } for m in metas]
    return make_meta(source='derived', confidence=confidence,
                     derived_from_mock=derived_from_mock, lineage=prior + input_steps)
