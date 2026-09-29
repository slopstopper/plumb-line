"""pytest_plugin — the fixture quarantine for pytest (#123).

Tests are where fake data is supposed to live; this makes the quarantine
explicit there. A fixture decorated with :func:`plumb_mock_fixture` hands the
test its value marked ``source='mock'``, so anything derived from it carries
the taint; :func:`assert_no_taint` fails a test when a golden output still
carries it, and :func:`assert_tainted` checks that the taint did reach a
value.

Owner decisions on #123: marking is opt-in per fixture; the plugin registers
itself through the package's ``pytest11`` entry point and adds no hooks,
fixtures or options; the assertion takes a marked value only (#544). The assertion is
the egress guard (#120, SPEC §5c) with its defaults. JS twin:
primitives/js/vitest.mjs.

This module imports pytest; the rest of the package never does, so the core
stays dependency-free.
"""
import functools
import inspect

import pytest

try:  # installed as a package (plumb_line_provenance)
    from .marked import mark
    from .guard import guard, ProvenanceRefused
    from .audit import validate_envelope
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from marked import mark
    from guard import guard, ProvenanceRefused
    from audit import validate_envelope

__all__ = ['plumb_mock_fixture', 'assert_no_taint', 'assert_tainted']

_NO_TAINT = 'no mock taint may reach a golden output'
_TAINTED = 'mock taint was expected to reach this value'


def _is_marked(value):
    # A marked value, not data that happens to have 'value' and 'meta' keys:
    # its meta must be a structurally valid envelope (SPEC §5a), read from the
    # dict's own storage as guard reads it. The JS twin makes the same
    # judgement on a plain object's own envelope fields.
    if not (isinstance(value, dict) and 'value' in value and 'meta' in value):
        return False
    meta = value['meta']
    return not validate_envelope(dict(dict.items(meta)) if isinstance(meta, dict) else meta)


def _quarantine(value):
    __tracebackhide__ = True
    # A marked value is refused, not re-marked: marking it again would nest it,
    # and marking a value someone labelled `real` as mock would hide that label.
    if _is_marked(value):
        raise TypeError('plumb_mock_fixture: the fixture returned a marked value; '
                        'return the raw value and let the decorator mark it mock')
    return mark(value, source='mock')


def _source(fn):
    try:
        return inspect.getsource(fn)
    except (OSError, TypeError):
        return fn.__name__


def _marking(fn, name):
    # `name` is the fixture's name (pytest.fixture's `name=`, else the
    # function's), which pytest's own messages use.
    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
        raise TypeError('plumb_mock_fixture does not support async fixtures')
    if inspect.isgeneratorfunction(fn):
        @functools.wraps(fn)
        def yielding(*args, **kwargs):
            __tracebackhide__ = True
            gen = fn(*args, **kwargs)
            try:
                value = next(gen)
            except StopIteration:
                # pytest's own wording, not a bare StopIteration.
                raise ValueError(f'{name} did not yield a value') from None
            try:
                marked = _quarantine(value)
            except BaseException:
                # Run the fixture's own cleanup now, not at collection; a
                # failing cleanup must not replace the reason marking failed.
                try:
                    gen.close()
                except Exception:
                    pass
                raise
            yield marked
            # The rest of the fixture is its teardown, run as pytest runs it:
            # a second yield is reported with the fixture's own source.
            try:
                next(gen)
            except StopIteration:
                return
            pytest.fail(f"fixture function has more than one 'yield':\n\n{_source(fn)}", pytrace=False)
        return yielding

    @functools.wraps(fn)
    def returning(*args, **kwargs):
        __tracebackhide__ = True
        return _quarantine(fn(*args, **kwargs))
    return returning


def plumb_mock_fixture(fixture_function=None, **fixture_kwargs):
    """``pytest.fixture``, with the fixture's value marked ``source='mock'``.

    Use it as ``@plumb_mock_fixture`` or ``@plumb_mock_fixture(scope=...)``;
    keyword arguments go to ``pytest.fixture``. A generator fixture's yielded
    value is marked and its teardown still runs. A fixture that returns a
    value already marked is an error.
    """
    def decorate(fn):
        return pytest.fixture(**fixture_kwargs)(_marking(fn, fixture_kwargs.get('name') or fn.__name__))
    return decorate(fixture_function) if fixture_function is not None else decorate


def assert_no_taint(output):
    """Fail the test unless ``output`` may leave through an output point.

    It is ``guard(output)`` with its defaults (#120): mock taint anywhere in
    the envelope or its lineage fails, as does an unmarked or malformed value.
    Raises ``AssertionError`` listing guard's reasons; returns ``None``.
    """
    __tracebackhide__ = True  # report the failure at the test, not here
    try:
        guard(output)
    except ProvenanceRefused as e:
        raise AssertionError(f'{_NO_TAINT}: {e}') from None


def assert_tainted(output):
    """Fail the test unless guard refuses ``output`` for mock taint.

    The claim that a fixture's taint reached a value, verified: a value guard
    lets through fails, and so does one it refuses for another reason
    (unmarked, malformed), which is not proof. The twin of JS's assertTainted
    and ``expect(x).not.toBeUntainted()``. Returns ``None``.
    """
    __tracebackhide__ = True
    try:
        guard(output)
    except ProvenanceRefused as e:
        if any(r.startswith('mock:') for r in e.reasons):
            return
        raise AssertionError(f'{_TAINTED}: guard refused it, but not for mock taint: {e}') from None
    raise AssertionError(f'{_TAINTED}: guard let it through')
