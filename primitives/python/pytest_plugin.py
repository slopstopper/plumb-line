"""pytest_plugin — the fixture quarantine for pytest (#123).

Tests are where fake data is supposed to live; this makes the quarantine
explicit there. A fixture decorated with :func:`plumb_mock_fixture` hands the
test its value marked ``source='mock'``, so anything derived from it carries
the taint; :func:`assert_no_taint` fails a test when a golden output still
carries it.

Owner decisions on #123: marking is opt-in per fixture; the plugin registers
itself through the package's ``pytest11`` entry point and is inert unless a
test uses it; the assertion takes a marked value only (#544). The assertion is
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
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from marked import mark
    from guard import guard, ProvenanceRefused

__all__ = ['plumb_mock_fixture', 'assert_no_taint']


def _is_marked(value):
    return isinstance(value, dict) and 'value' in value and 'meta' in value


def _quarantine(value):
    # A marked value is refused, not re-marked: marking it again would nest it,
    # and marking a value someone labelled `real` as mock would hide that label.
    if _is_marked(value):
        raise TypeError('plumb_mock_fixture: the fixture returned a marked value; '
                        'return the raw value and let the decorator mark it mock')
    return mark(value, source='mock')


def _marking(fn):
    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
        raise TypeError('plumb_mock_fixture does not support async fixtures')
    if inspect.isgeneratorfunction(fn):
        @functools.wraps(fn)
        def yielding(*args, **kwargs):
            gen = fn(*args, **kwargs)
            yield _quarantine(next(gen))
            # The rest of the fixture is its teardown.
            yield from gen
        return yielding

    @functools.wraps(fn)
    def returning(*args, **kwargs):
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
        return pytest.fixture(**fixture_kwargs)(_marking(fn))
    return decorate(fixture_function) if fixture_function is not None else decorate


def assert_no_taint(output):
    """Fail the test unless ``output`` may leave through an output point.

    It is ``guard(output)`` with its defaults (#120): mock taint anywhere in
    the envelope or its lineage fails, as does an unmarked or malformed value.
    Raises ``AssertionError`` listing guard's reasons; returns ``None``.
    """
    try:
        guard(output)
    except ProvenanceRefused as e:
        raise AssertionError(f'no mock taint may reach a golden output: {e}') from None
