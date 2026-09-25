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
    # baseline's names resolve lazily (__getattr__ below): imported here, the
    # module was already in sys.modules when `python -m
    # plumb_line_provenance.baseline` ran it as a script, and runpy printed a
    # RuntimeWarning on every CLI call (#439).
    _LAZY_BASELINE = True
except ImportError:  # flat usage (modules on sys.path)
    from provenance import (
        PROVENANCE_VERSION, STATUS, CONFIDENCE,
        make_meta, weakest_confidence, weakest_source,
        is_score, combine_confidence_score, taints, combine_provenance,
        reset_step_counter,
    )
    from marked import mark, unwrap, meta_of, derive
    from audit import audit_meta, validate_envelope
    from baseline import (
        check, assert_baseline, update, list_baselines, show, validate_baseline,
    )
    _LAZY_BASELINE = False

_BASELINE_NAMES = frozenset({
    'check', 'assert_baseline', 'update', 'list_baselines', 'show', 'validate_baseline',
})


def __getattr__(name):
    if _LAZY_BASELINE and name in _BASELINE_NAMES:
        from . import baseline as _baseline
        return getattr(_baseline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# The HTTP adapter shipped as `http.py`, which shadowed the stdlib `http`
# package whenever this directory was on sys.path (#171). It is now
# `http_adapter.py`; `plumb_line_provenance.http` stays importable as an alias
# so existing imports keep working. Importing it pulls in no optional
# dependency (requests/httpx are imported at call time). Guarded on its own:
# flat usage has no parent package, and the plugin bundle omits the adapter.
try:
    from . import http_adapter as http
except ImportError:
    pass
else:
    import sys as _sys
    _sys.modules[__name__ + '.http'] = http

__all__ = [
    'PROVENANCE_VERSION', 'STATUS', 'CONFIDENCE',
    'make_meta', 'weakest_confidence', 'weakest_source',
    'is_score', 'combine_confidence_score', 'taints', 'combine_provenance',
    'mark', 'unwrap', 'meta_of', 'derive', 'audit_meta', 'validate_envelope',
    'check', 'assert_baseline', 'update', 'list_baselines', 'show', 'validate_baseline',
]
# reset_step_counter is intentionally excluded from __all__: it is test-only
# infrastructure. Import it directly from .provenance when needed in test suites.
