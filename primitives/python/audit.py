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

    if meta.get('source') in CLEAN_SOURCES and meta.get('derived_from_mock') is True:
        issues.append(f"laundering: clean source '{meta.get('source')}' but derived_from_mock is true")

    lineage_confidences = [s.get('confidence') for s in lineage if s.get('confidence') in CONFIDENCE]
    if lineage_confidences:
        weakest = weakest_confidence(*lineage_confidences)
        c = meta.get('confidence')
        top_idx = CONFIDENCE.index(c) if c in CONFIDENCE else -1
        if top_idx > CONFIDENCE.index(weakest):
            issues.append(f"over-claiming: confidence '{c}' exceeds weakest lineage confidence '{weakest}'")

    # Numeric over-claiming — the higher-resolution analog of the ordinal check.
    if is_score(meta.get('confidence_score')):
        lineage_scores = [s.get('confidence_score') for s in lineage if is_score(s.get('confidence_score'))]
        if lineage_scores:
            weakest = min(lineage_scores)
            if meta['confidence_score'] > weakest:
                issues.append(f"over-claiming: confidenceScore {meta['confidence_score']} exceeds weakest lineage score {weakest}")

    # Source over-claim — weakest_source cannot look cleaner than the lineage proves.
    if meta.get('weakest_source') in STATUS:
        actual = weakest_source(*[s.get('source') for s in lineage])
        if actual is not None and STATUS.index(meta['weakest_source']) > STATUS.index(actual):
            issues.append(f"source over-claim: weakestSource '{meta['weakest_source']}' is cleaner than lineage's '{actual}'")

    lineage_tainted = any(bool(s.get('derived_from_mock')) or s.get('source') == 'mock' for s in lineage)
    if lineage_tainted and meta.get('derived_from_mock') is False:
        issues.append('taint dropped: lineage contains a tainted step but derived_from_mock is false')

    if meta.get('source') == 'derived' and len(lineage) == 0:
        issues.append('unreproducible: derived value has no lineage')

    return issues
