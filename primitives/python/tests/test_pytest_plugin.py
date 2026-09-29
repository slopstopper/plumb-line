"""test_pytest_plugin — the fixture quarantine for pytest (#123).

Owner decisions on #123: marking is opt-in per fixture (`plumb_mock_fixture`);
the plugin registers itself through the package's `pytest11` entry point; the
no-taint assertion takes a marked value only (#544 assesses walking a
structure). The assertion is `guard` (#120) with its defaults. JS twin:
primitives/js/vitest.test.mjs.

Fixture behaviour is exercised in a child pytest run (pytester, in a
subprocess), since a fixture only exists inside a session.
"""
import os
import subprocess
import sys

import pytest

_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PY_DIR)
from marked import mark, derive  # noqa: E402
from pytest_plugin import assert_no_taint  # noqa: E402

pytest_plugins = ["pytester"]


def _session(pytester, body):
    pytester.makeconftest(f"import sys\nsys.path.insert(0, {_PY_DIR!r})\n")
    pytester.makepyfile(body)
    return pytester.runpytest_subprocess("-p", "no:cacheprovider", "-p", "no:randomly")


def test_a_decorated_fixture_hands_the_test_a_value_marked_mock(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture
from marked import meta_of, unwrap

@plumb_mock_fixture
def rate():
    return 1.17

def test_it(rate):
    assert unwrap(rate) == 1.17
    assert meta_of(rate)["source"] == "mock"
    assert meta_of(rate)["derived_from_mock"] is True
''')
    result.assert_outcomes(passed=1)


def test_fixture_options_pass_through_and_a_generator_fixture_still_tears_down(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture
from marked import meta_of, unwrap

LOG = []

@plumb_mock_fixture(scope="module")
def rows():
    LOG.append("setup")
    yield [1, 2]
    LOG.append("teardown")

def test_first(rows):
    assert unwrap(rows) == [1, 2] and meta_of(rows)["source"] == "mock"

def test_second(rows):
    assert LOG == ["setup"]  # module scope: set up once

def test_after():
    pass

def teardown_module():
    assert LOG == ["setup", "teardown"]
''')
    result.assert_outcomes(passed=3)


def test_a_fixture_that_returns_a_marked_value_fails_loudly(pytester):
    # Re-marking would nest a marked value inside another, and marking a value
    # someone labelled `real` as mock would hide that label, not quarantine it.
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture
from marked import mark

@plumb_mock_fixture
def already():
    return mark(1, source="real", confidence="high")

def test_it(already):
    pass
''')
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*plumb_mock_fixture: the fixture returned a marked value*"])


def test_an_async_fixture_is_refused_at_decoration(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture

@plumb_mock_fixture
async def later():
    return 1

def test_it():
    pass
''')
    result.stdout.fnmatch_lines(["*plumb_mock_fixture does not support async fixtures*"])
    assert result.ret != 0


def test_assert_no_taint_passes_a_clean_value_and_returns_nothing():
    assert assert_no_taint(mark(1, source="real", confidence="high")) is None


def test_assert_no_taint_fails_a_value_derived_from_mock_with_the_guard_reasons():
    rate = mark(1.17, source="mock")
    total = derive([mark(100, source="real", confidence="high"), rate], lambda a, r: a * r)
    with pytest.raises(AssertionError) as e:
        assert_no_taint(total)
    assert str(e.value).startswith("no mock taint may reach a golden output: provenance refused: ")
    assert "mock:" in str(e.value)


def test_assert_no_taint_fails_an_unmarked_value():
    with pytest.raises(AssertionError, match="not a marked value"):
        assert_no_taint(42)


def test_assert_no_taint_raises_an_assertion_error_not_a_refusal():
    # A test failure, reported as one; `from None`, so the report is the reasons.
    with pytest.raises(AssertionError) as e:
        assert_no_taint(mark(1, source="mock"))
    assert not isinstance(e.value, ValueError)
    assert e.value.__cause__ is None and e.value.__suppress_context__


def test_the_plugin_registers_itself_through_the_pytest11_entry_point():
    with open(os.path.join(_PY_DIR, "pyproject.toml"), encoding="utf-8") as fh:
        text = fh.read()
    assert '[project.entry-points.pytest11]' in text
    assert 'plumb_line_provenance = "plumb_line_provenance.pytest_plugin"' in text


def test_the_package_import_never_imports_pytest():
    # The core stays dependency-free: only the plugin module imports pytest.
    out = subprocess.run([sys.executable, '-c', (
        'import importlib.util, os, sys\n'
        'sys.modules["pytest"] = None\n'  # any `import pytest` now fails
        'spec = importlib.util.spec_from_file_location("plumb_line_provenance", "__init__.py",'
        ' submodule_search_locations=[os.getcwd()])\n'
        'pkg = importlib.util.module_from_spec(spec); sys.modules["plumb_line_provenance"] = pkg\n'
        'spec.loader.exec_module(pkg)\n'
        'from plumb_line_provenance import guard, mark\n'
        'print("ok")\n')], cwd=_PY_DIR, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == 'ok'


def test_the_plugin_loads_under_its_published_name():
    out = subprocess.run([sys.executable, '-c', (
        'import importlib.util, os, sys\n'
        'spec = importlib.util.spec_from_file_location("plumb_line_provenance", "__init__.py",'
        ' submodule_search_locations=[os.getcwd()])\n'
        'pkg = importlib.util.module_from_spec(spec); sys.modules["plumb_line_provenance"] = pkg\n'
        'spec.loader.exec_module(pkg)\n'
        'from plumb_line_provenance.pytest_plugin import plumb_mock_fixture, assert_no_taint\n'
        'print("ok")\n')], cwd=_PY_DIR, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == 'ok'
