"""plumb-line provenance primitive — public API.

Importable as a package once installed (`from plumb_line_provenance import mark`),
or copy the module files into a project and import them flat (`from marked import
mark`). Both work; the modules carry a dual-import shim. See ../SPEC.md.
"""
try:  # installed as a package
    from .provenance import (
        PROVENANCE_VERSION, STATUS, CONFIDENCE,
        make_meta, weakest_confidence, weakest_source,
        is_score, combine_confidence_score, taints, combine_provenance,
        reset_step_counter,
    )
    from .marked import mark, unwrap, meta_of, derive
    from .audit import audit_meta, validate_envelope
except ImportError:  # flat usage (modules on sys.path)
    from provenance import (
        PROVENANCE_VERSION, STATUS, CONFIDENCE,
        make_meta, weakest_confidence, weakest_source,
        is_score, combine_confidence_score, taints, combine_provenance,
        reset_step_counter,
    )
    from marked import mark, unwrap, meta_of, derive
    from audit import audit_meta, validate_envelope

__all__ = [
    'PROVENANCE_VERSION', 'STATUS', 'CONFIDENCE',
    'make_meta', 'weakest_confidence', 'weakest_source',
    'is_score', 'combine_confidence_score', 'taints', 'combine_provenance',
    'mark', 'unwrap', 'meta_of', 'derive', 'audit_meta', 'validate_envelope',
]
# reset_step_counter is intentionally excluded from __all__: it is test-only
# infrastructure. Import it directly from .provenance when needed in test suites.
