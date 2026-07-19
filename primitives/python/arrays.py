"""arrays — numpy ndarray provenance adapter (see ADR-0013).

`PlumbArray` wraps an ndarray with a standard provenance envelope; the explicit
combinators (`plumb_concatenate`/`plumb_stack`/`plumb_derive`) run the numpy
operation on the values and the existing combination law on the metas. `numpy` is
a guarded optional import (`pip install "plumb-line-provenance[numpy]"`); importing
this module needs no third-party package."""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import make_meta
    from .marked import derive
    from .audit import audit_meta
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from provenance import make_meta
    from marked import derive
    from audit import audit_meta

_NUMPY_HINT = ('needs numpy; install it with: '
               'pip install "plumb-line-provenance[numpy]"')


class PlumbArray:
    """A numpy ndarray carrying a provenance envelope. `.value` is the array;
    `.meta` is the standard envelope (audit_meta/validate_envelope work on it)."""

    def __init__(self, value, source='derived', confidence='none', **meta_input):
        try:
            import numpy
        except ImportError as e:  # pragma: no cover - exercised in the no-extras CI guard
            raise ImportError('PlumbArray ' + _NUMPY_HINT) from e
        if not isinstance(value, numpy.ndarray):
            raise TypeError(f'PlumbArray expects a numpy.ndarray, got {type(value).__name__}')
        self.value = value
        self.meta = make_meta(source=source, confidence=confidence, **meta_input)

    @classmethod
    def _wrap(cls, value, meta):
        """Wrap an already-computed (value, meta) without re-validating — internal
        use by the combinators."""
        obj = cls.__new__(cls)
        obj.value = value
        obj.meta = meta
        return obj

    def unwrap(self):
        return self.value

    def meta_of(self):
        return self.meta

    def audit(self):
        return audit_meta(self.meta)

    def __repr__(self):
        m = self.meta
        return (f"PlumbArray(source={m['source']!r}, confidence={m['confidence']!r}, "
                f"derived_from_mock={m['derived_from_mock']!r}, value=<ndarray {self.value.shape}>)")


def plumb_derive(inputs, fn, **meta_override):
    """General combinator: run `fn` on the unwrapped arrays, run the combination
    law on the metas (via `marked.derive`), return a PlumbArray. Taint is
    force-OR'd and cannot be cleared via override (SPEC §3 rule 1).

    The result is wrapped as-is: `fn`'s return type is NOT re-validated, so a
    reducing `fn` (e.g. `lambda a: a.sum()`) yields a PlumbArray whose `.value`
    is a numpy scalar — the provenance still propagates correctly."""
    marked_inputs = [{'value': i.value, 'meta': i.meta} for i in inputs]
    result = derive(marked_inputs, fn, **meta_override)
    return PlumbArray._wrap(result['value'], result['meta'])


def plumb_concatenate(objs, **kwargs):
    """Provenance-propagating `numpy.concatenate` over PlumbArrays."""
    try:
        import numpy
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI guard
        raise ImportError('plumb_concatenate ' + _NUMPY_HINT) from e
    return plumb_derive(objs, lambda *arrs: numpy.concatenate(list(arrs), **kwargs))


def plumb_stack(objs, **kwargs):
    """Provenance-propagating `numpy.stack` over PlumbArrays."""
    try:
        import numpy
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI guard
        raise ImportError('plumb_stack ' + _NUMPY_HINT) from e
    return plumb_derive(objs, lambda *arrs: numpy.stack(list(arrs), **kwargs))
