"""test_pytest_plugin — the fixture quarantine for pytest (#123).

Owner decisions on #123: marking is opt-in per fixture (`plumb_mock_fixture`);
the plugin registers itself through the package's `pytest11` entry point; the
no-taint assertion takes a marked value only (#544 assesses walking a
structure). The assertion is `guard` (#120) with its defaults. JS twin:
primitives/js/vitest.test.mjs.

Fixture behaviour is exercised in a child pytest run (pytester, in a
subprocess), since a fixture only exists inside a session.
"""
import json
import os
import subprocess
import sys

import pytest

_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PY_DIR)
from marked import mark, derive  # noqa: E402
from pytest_plugin import assert_no_taint, assert_tainted  # noqa: E402

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
    # Names the fixture, so a test using several can tell which one.
    result.stdout.fnmatch_lines(["*plumb_mock_fixture: fixture 'already' returned a marked value*"])


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


# --- the plugin as installed: loaded by its entry point, turned off by -p no: --
#
# The README and docs/api.md say the plugin loads at every pytest start where
# the package is installed, that `-p no:plumb_line_provenance.pytest_plugin`
# turns it off, and that naming it in `-p` or `pytest_plugins` as well is
# harmless (#597). These run real pytest sessions against an install of the
# package. The install is made here, without network: the package's modules,
# from the source dir `[tool.setuptools]` maps it to, copied under
# `plumb_line_provenance/` beside a `.dist-info` whose entry_points.txt is
# written from pyproject.toml's `[project.entry-points]` tables, the file
# setuptools writes from them. pytest finds it through importlib.metadata, as
# it finds any installed plugin. What this does not exercise is the setuptools
# build itself: setuptools is not in requirements-test.txt, and a real install
# in a fresh venv would fetch it from the network.

_PLUGIN = "plumb_line_provenance.pytest_plugin"

_REPORT = '''
import json, sys
from importlib.metadata import entry_points

def test_report(pytestconfig):
    pm = pytestconfig.pluginmanager
    plugin = pm.get_plugin("plumb_line_provenance.pytest_plugin")
    print("PLUMB " + json.dumps({
        "registered": plugin is not None,
        "names": sorted(n for n, p in pm.list_name_plugin()
                        if p is sys.modules.get("plumb_line_provenance.pytest_plugin")),
        "file": getattr(plugin, "__file__", None),
        "dists": sorted(d.metadata["Name"] for _, d in pm.list_plugin_distinfo()),
        "package_imported": "plumb_line_provenance" in sys.modules,
        "visible": sorted(ep.name for ep in entry_points(group="pytest11")
                          if ep.dist and ep.dist.metadata["Name"] == "plumb-line-provenance"),
    }))
'''


def _install(site):
    import shutil
    import tomllib
    with open(os.path.join(_PY_DIR, "pyproject.toml"), "rb") as fh:
        config = tomllib.load(fh)
    project, tools = config["project"], config["tool"]["setuptools"]
    # The package as pyproject.toml maps it: its import name, from its source dir.
    assert tools["packages"] == ["plumb_line_provenance"], tools["packages"]
    src = os.path.join(_PY_DIR, tools.get("package-dir", {}).get("plumb_line_provenance", "plumb_line_provenance"))
    pkg = site / "plumb_line_provenance"
    pkg.mkdir(parents=True)
    for name in os.listdir(src):
        if name.endswith(".py"):
            shutil.copy(os.path.join(src, name), pkg / name)
    info = site / f"plumb_line_provenance-{project['version']}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {project['name']}\nVersion: {project['version']}\n")
    (info / "entry_points.txt").write_text("".join(
        f"[{group}]\n" + "".join(f"{k} = {v}\n" for k, v in eps.items()) + "\n"
        for group, eps in project.get("entry-points", {}).items()))
    return pkg


def _installed_session(pytester, monkeypatch, *args, conftest=""):
    site = pytester.path.parent / f"{pytester.path.name}-site"
    pkg = _install(site)
    monkeypatch.setenv("PYTHONPATH", str(site))
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    if conftest:
        pytester.makeconftest(conftest)
    pytester.makepyfile(_REPORT)
    result = pytester.runpytest_subprocess("-s", "-p", "no:cacheprovider", "-p", "no:randomly", *args)
    # -s output shares the line pytest opened for the test file.
    lines = [ln.split("PLUMB ", 1)[1] for ln in result.outlines if "PLUMB {" in ln]
    assert len(lines) == 1, result.stdout.str() + result.stderr.str()
    report = json.loads(lines[0])
    return result, report, str(pkg)


def test_the_installed_plugin_loads_through_its_entry_point_at_every_pytest_start(pytester, monkeypatch):
    # The session's tests never import the package; only the entry point can load it.
    result, report, pkg = _installed_session(pytester, monkeypatch)
    result.assert_outcomes(passed=1)
    assert report["registered"] and report["package_imported"]
    assert report["file"].startswith(pkg)
    assert report["visible"] == [_PLUGIN]
    assert "plumb-line-provenance" in report["dists"]  # loaded as an installed dist's entry point
    assert report["names"] == [_PLUGIN]  # under the module's own name


def test_dash_p_no_with_the_module_name_turns_the_installed_plugin_off(pytester, monkeypatch):
    result, report, _ = _installed_session(pytester, monkeypatch, "-p", f"no:{_PLUGIN}")
    result.assert_outcomes(passed=1)
    assert report["visible"] == [_PLUGIN]  # installed, its entry point there to load
    assert not report["registered"]
    assert not report["package_imported"]  # not loaded, so the package is not imported either
    assert "plumb-line-provenance" not in report["dists"]


@pytest.mark.parametrize("how", ["-p", "pytest_plugins"])
def test_naming_the_installed_plugin_explicitly_as_well_is_harmless(pytester, monkeypatch, how):
    # pytest registers an entry-point plugin under the entry point's key and
    # an explicit one (`-p ...`, `pytest_plugins = [...]`) under its module
    # name. Were the two different, the second registration would abort the
    # session ("Plugin already registered under a different name"); equal,
    # pytest sees the name taken and skips it.
    if how == "-p":
        result, report, _ = _installed_session(pytester, monkeypatch, "-p", _PLUGIN)
    else:
        result, report, _ = _installed_session(
            pytester, monkeypatch, conftest=f"pytest_plugins = [{_PLUGIN!r}]\n")
    assert result.ret == 0, result.stdout.str() + result.stderr.str()
    result.assert_outcomes(passed=1)
    assert report["names"] == [_PLUGIN]  # registered once


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


# --- "already marked" means a real envelope: mirrored in vitest.test.mjs ---

class _Box:
    def __init__(self):
        self.value = 1


@pytest.mark.parametrize("data", [
    {"value": 42, "label": "x"},                 # an option-list entry
    {"value": 3, "meta": {"page": 1}},           # a paged JSON payload
    {"value": 1, "meta": "not an envelope"},
    _Box(),                                      # an object with a `value` field
])
def test_ordinary_fixture_data_shaped_like_a_marked_value_is_marked_not_refused(data):
    from pytest_plugin import _quarantine
    from marked import meta_of, unwrap
    marked = _quarantine(data, "data")
    assert unwrap(marked) == data and meta_of(marked)["source"] == "mock"


def test_only_a_real_marked_value_is_refused():
    from pytest_plugin import _quarantine
    with pytest.raises(TypeError, match="fixture 'rate' returned a marked value"):
        _quarantine(mark(1, source="real", confidence="high"), "rate")


def test_a_generator_fixture_that_never_yields_reports_it_as_pytest_does(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture

@plumb_mock_fixture
def empty():
    return
    yield

def test_it(empty):
    pass
''')
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*did not yield a value*"])
    result.stdout.no_fnmatch_line("*RuntimeError*")


def test_a_failing_assertion_is_reported_at_the_test_not_in_the_plugin(pytester):
    result = _session(pytester, '''
from pytest_plugin import assert_no_taint
from marked import mark

def test_it():
    assert_no_taint(mark(1, source="mock"))
''')
    result.assert_outcomes(failed=1)
    result.stdout.no_fnmatch_line("*pytest_plugin.py:*")


# --- assert_tainted: the positive claim, verified (twin: assertTainted) -----

def test_assert_tainted_passes_only_when_guard_refuses_for_mock_taint():
    total = derive([mark(100, source="real", confidence="high"), mark(1.17, source="mock")],
                   lambda a, r: a * r)
    assert assert_tainted(total) is None


@pytest.mark.parametrize("output", [42, None, {"value": 1, "meta": {}}])
def test_assert_tainted_fails_a_value_guard_refuses_for_another_reason(output):
    with pytest.raises(AssertionError, match="^mock taint was expected to reach this value: "
                                             "guard refused it, but not for mock taint"):
        assert_tainted(output)


def test_assert_tainted_fails_a_clean_value():
    with pytest.raises(AssertionError, match="^mock taint was expected to reach this value: guard let it through"):
        assert_tainted(mark(1, source="real", confidence="high"))


def test_a_renamed_fixture_that_never_yields_is_reported_by_its_fixture_name(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture

@plumb_mock_fixture(name="named")
def _never():
    if False:
        yield

def test_it(named):
    pass
''')
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*named did not yield a value*"])


def test_a_fixture_that_yields_twice_is_reported_with_its_own_source(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture

@plumb_mock_fixture
def twice():
    yield 1
    yield 2

def test_it(twice):
    pass
''')
    result.stdout.fnmatch_lines(["*fixture function has more than one 'yield'*"])
    result.stdout.fnmatch_lines(["*    yield 2*"])  # indented, as pytest does
    # pytest's location: the fixture's first line, its decorator (line 3).
    result.stdout.fnmatch_lines(["*test_a_fixture_that_yields_twice_is_reported_with_its_own_source.py:3"])
    result.stdout.no_fnmatch_line("*yield from gen*")


def test_the_fixture_cleanup_runs_at_once_when_marking_fails_and_its_error_does_not_hide_the_cause(pytester):
    result = _session(pytester, '''
from pytest_plugin import plumb_mock_fixture
from marked import mark

CLEANED = []

@plumb_mock_fixture
def already():
    try:
        yield mark(1, source="real", confidence="high")
    finally:
        CLEANED.append(True)
        raise OSError("cleanup boom")

def test_it(already):
    pass

def test_cleaned_at_once():
    assert CLEANED == [True]
''')
    result.assert_outcomes(passed=1, errors=1)
    # The refusal is the reported error, with the cleanup's failure attached
    # as a note; before, the OSError was the error and the refusal only its
    # context.
    result.stdout.fnmatch_lines(["E   TypeError: plumb_mock_fixture: fixture 'already'*"])
    result.stdout.fnmatch_lines(["*the fixture's own cleanup then failed: OSError('cleanup boom')*"])
    result.stdout.no_fnmatch_line("E   OSError*")


def test_a_skip_in_the_fixture_cleanup_cannot_hide_the_refusal_behind_skipped(pytester):
    result = _session(pytester, '''
import pytest
from pytest_plugin import plumb_mock_fixture
from marked import mark

@plumb_mock_fixture
def already():
    try:
        yield mark(1, source="real", confidence="high")
    finally:
        pytest.skip("cleanup skipped")

def test_it(already):
    pass
''')
    result.assert_outcomes(errors=1)  # before: skipped, the refusal nowhere
    result.stdout.fnmatch_lines(["E   TypeError: plumb_mock_fixture: fixture 'already'*"])


def test_assert_tainted_is_reported_at_the_test_not_in_the_plugin(pytester):
    result = _session(pytester, '''
from pytest_plugin import assert_tainted
from marked import mark

def test_it():
    assert_tainted(mark(1, source="real", confidence="high"))
''')
    result.assert_outcomes(failed=1)
    result.stdout.no_fnmatch_line("*pytest_plugin.py:*")


def test_already_marked_reads_the_dicts_own_contents_as_guard_does():
    from pytest_plugin import _is_marked

    class Hide(dict):
        def __contains__(self, key):
            return key != "source" and dict.__contains__(self, key)

    meta = mark(1, source="real", confidence="high")["meta"]
    assert _is_marked({"value": 1, "meta": Hide(meta)})

