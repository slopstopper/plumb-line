"""frames — pandas DataFrame provenance adapter (see ADR-0013).

`PlumbDataFrame` wraps a DataFrame with a standard provenance envelope; the
explicit combinators (`plumb_concat`/`plumb_merge`/`plumb_derive`) run the pandas
operation on the values and the existing combination law on the metas. `pandas` is
a guarded optional import (`pip install "plumb-line-provenance[pandas]"`); importing
this module needs no third-party package."""
try:  # installed as a package (plumb_line_provenance)
    from .provenance import make_meta
    from .marked import derive
    from .audit import audit_meta
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from provenance import make_meta
    from marked import derive
    from audit import audit_meta

_PANDAS_HINT = ('needs pandas; install it with: '
                'pip install "plumb-line-provenance[pandas]"')


class PlumbDataFrame:
    """A pandas DataFrame carrying a provenance envelope. `.value` is the frame;
    `.meta` is the standard envelope (audit_meta/validate_envelope work on it)."""

    def __init__(self, value, source='derived', confidence='none', **meta_input):
        try:
            import pandas
        except ImportError as e:  # pragma: no cover - exercised in the no-extras CI guard
            raise ImportError('PlumbDataFrame ' + _PANDAS_HINT) from e
        if not isinstance(value, pandas.DataFrame):
            raise TypeError(f'PlumbDataFrame expects a pandas.DataFrame, got {type(value).__name__}')
        self.value = value
        self.meta = make_meta(source=source, confidence=confidence, **meta_input)

    @classmethod
    def _wrap(cls, value, meta):
        """Wrap an already-computed (value, meta) without re-validating — internal
        use by the combinators, where `meta` is a finished combine_provenance
        result and `value` came from the caller's transform."""
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
        return (f"PlumbDataFrame(source={m['source']!r}, confidence={m['confidence']!r}, "
                f"derived_from_mock={m['derived_from_mock']!r}, value=<DataFrame {self.value.shape}>)")


def plumb_derive(inputs, fn, **meta_override):
    """General combinator: run `fn` on the unwrapped frames, run the combination
    law on the metas (via `marked.derive`), return a PlumbDataFrame. Taint is
    force-OR'd and cannot be cleared via override (SPEC §3 rule 1).

    The result is wrapped as-is: `fn`'s return type is NOT re-validated, so a
    reducing `fn` (e.g. `lambda d: d.sum()`) yields a PlumbDataFrame whose
    `.value` is a Series — the provenance still propagates correctly."""
    marked_inputs = [{'value': i.value, 'meta': i.meta} for i in inputs]
    result = derive(marked_inputs, fn, **meta_override)
    return PlumbDataFrame._wrap(result['value'], result['meta'])


def plumb_concat(objs, **kwargs):
    """Provenance-propagating `pandas.concat` over PlumbDataFrames."""
    try:
        import pandas
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI guard
        raise ImportError('plumb_concat ' + _PANDAS_HINT) from e
    return plumb_derive(objs, lambda *dfs: pandas.concat(list(dfs), **kwargs))


def plumb_merge(left, right, **kwargs):
    """Provenance-propagating `DataFrame.merge` of two PlumbDataFrames."""
    return plumb_derive([left, right], lambda a, b: a.merge(b, **kwargs))
