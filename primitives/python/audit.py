"""audit — runtime consistency checker for provenance metadata. Mirror of audit.mjs."""
from provenance import CONFIDENCE, weakest_confidence

CLEAN_SOURCES = ['real', 'semiReal', 'fallback']

def audit_meta(meta):
    if meta is None:
        return ['missing meta']
    issues = []
    lineage = meta.get('lineage') if isinstance(meta.get('lineage'), list) else []

    if meta.get('source') in CLEAN_SOURCES and meta.get('derived_from_mock') is True:
        issues.append(f"laundering: clean source '{meta.get('source')}' but derived_from_mock is true")

    lineage_confidences = [s.get('confidence') for s in lineage if s.get('confidence') in CONFIDENCE]
    if lineage_confidences:
        weakest = weakest_confidence(*lineage_confidences)
        c = meta.get('confidence')
        top_idx = CONFIDENCE.index(c) if c in CONFIDENCE else -1
        if top_idx > CONFIDENCE.index(weakest):
            issues.append(f"over-claiming: confidence '{c}' exceeds weakest lineage confidence '{weakest}'")

    lineage_tainted = any(bool(s.get('derived_from_mock')) or s.get('source') == 'mock' for s in lineage)
    if lineage_tainted and meta.get('derived_from_mock') is False:
        issues.append('taint dropped: lineage contains a tainted step but derived_from_mock is false')

    if meta.get('source') == 'derived' and len(lineage) == 0:
        issues.append('unreproducible: derived value has no lineage')

    return issues
