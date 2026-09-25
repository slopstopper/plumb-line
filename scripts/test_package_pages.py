"""The npm and PyPI package pages cannot drift from the packages (#439).

Each registry page is rebuilt on publish from the package's own README and
manifest (primitives/js/{README.md,package.json},
primitives/python/{README.md,pyproject.toml}). Until 0.11.3 nothing checked
them, and they drifted: the PyPI page never mentioned the baseline module the
package exports, carried a repo-relative link the registry cannot resolve,
and the npm page stated a Node floor the manifest contradicts and a CLI
command that does not run from an install.

Run from the repo root: python3 -m pytest -q scripts/test_package_pages.py
"""
import json
import os
import re

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JS = os.path.join(_ROOT, "primitives", "js")
_PY = os.path.join(_ROOT, "primitives", "python")
HOMEPAGE = "https://slopstopper.org/plumb-line/"  # owner decision on #439


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


JS_README = _read(_JS, "README.md")
PY_README = _read(_PY, "README.md")
PACKAGE = json.loads(_read(_JS, "package.json"))
READMES = {"npm": JS_README, "pypi": PY_README}

# Each optional feature and the heading its page section must carry. A new
# public module or subpath must be added here, which forces its page section.
PY_MODULE_SECTIONS = {
    "baseline": "Golden baseline",
    "http_adapter": "HTTP ingestion",
    "frames": "Dataframe adapters",
    "arrays": "Dataframe adapters",
}
PY_CORE = {"__init__", "provenance", "marked", "audit"}
JS_SUBPATH_SECTIONS = {"./http": "HTTP ingestion", "./baseline": "Golden baseline"}


def _links(text):
    """Every link target, in each form a registry renders: inline `[x](u)`,
    reference-style `[x]: u`, and HTML `href=`/`src=`."""
    return (re.findall(r"\]\(([^)\s]+)\)", text)
            + re.findall(r"^\s*\[[^\]]+\]:\s*(\S+)", text, re.M)
            + re.findall(r"(?:href|src)=[\"']([^\"']+)[\"']", text))


@pytest.mark.parametrize("page", sorted(READMES))
def test_no_repo_relative_links(page):
    # Registries render the README outside the repository: a relative link
    # resolves against the registry's own site and goes nowhere.
    bad = [u for u in _links(READMES[page]) if not re.match(r"(https?://|mailto:|#)", u)]
    assert not bad, f"{page} README has links the registry cannot resolve: {bad}"


@pytest.mark.parametrize("page", sorted(READMES))
def test_page_points_at_the_project(page):
    assert HOMEPAGE in READMES[page], f"{page} README should link the project page {HOMEPAGE}"


def test_npm_homepage():
    assert PACKAGE["homepage"] == HOMEPAGE


@pytest.mark.skipif(tomllib is None, reason="tomllib needs Python 3.11+")
def test_pypi_homepage():
    urls = tomllib.loads(_read(_PY, "pyproject.toml"))["project"]["urls"]
    assert urls["Homepage"] == HOMEPAGE


def test_node_floor_stated_on_the_page_matches_engines():
    floor = re.match(r">=\s*(\d+)", PACKAGE["engines"]["node"]).group(1)
    stated = re.findall(r"Node(?:\.js)?\s*(?:≥|>=)?\s*(\d+)\+?", JS_README)
    assert stated, "the npm page must state the Node floor"
    assert all(n == floor for n in stated), f"README states Node {stated}, engines says >= {floor}"


def test_every_public_python_module_has_a_page_section():
    modules = {f[:-3] for f in os.listdir(_PY) if f.endswith(".py")} - PY_CORE
    assert modules == set(PY_MODULE_SECTIONS), (
        f"public modules {sorted(modules)} vs sections mapped {sorted(PY_MODULE_SECTIONS)}: "
        f"add the new module's page section and map it here")
    for module, heading in PY_MODULE_SECTIONS.items():
        assert re.search(r"^## .*%s" % re.escape(heading), PY_README, re.M), \
            f"PyPI page has no '{heading}' section for {module}"


def test_every_js_subpath_has_a_page_section():
    subpaths = set(PACKAGE["exports"]) - {"."}
    assert subpaths == set(JS_SUBPATH_SECTIONS), (
        f"exports {sorted(subpaths)} vs sections mapped {sorted(JS_SUBPATH_SECTIONS)}")
    for subpath, heading in JS_SUBPATH_SECTIONS.items():
        assert re.search(r"^## .*%s" % re.escape(heading), JS_README, re.M), \
            f"npm page has no '{heading}' section for {subpath}"


def test_features_shared_by_both_packages_appear_on_both_pages():
    for heading in ("HTTP ingestion", "Golden baseline"):
        for page, text in READMES.items():
            assert re.search(r"^## .*%s" % re.escape(heading), text, re.M), f"{page}: {heading}"


def test_npm_cli_command_runs_from_an_install():
    # No `bin` entry, so the CLI is reached by path inside node_modules; a
    # bare `node baseline-cli.mjs` only works inside this repository.
    cli = "baseline-cli.mjs"
    assert cli in PACKAGE["files"]
    # Inline code spans and fenced lines alike.
    cmds = (re.findall(r"`(node [^`\n]*%s[^`\n]*)`" % re.escape(cli), JS_README)
            + re.findall(r"^\s*(node \S*%s.*)$" % re.escape(cli), JS_README, re.M))
    assert cmds, "the npm page should show how to run the baseline CLI"
    for cmd in cmds:
        assert "node_modules/plumb-line-provenance/" + cli in cmd or "bin" in PACKAGE, cmd


def test_npm_page_never_derives_from_an_async_body_read():
    # derive() is synchronous: derive([tagged], (r) => r.json()) marks a
    # Promise. The page showed exactly that until 0.11.3.
    assert not re.search(r"derive\([^)]*\)\s*=>\s*\w+\.json\(\)", JS_README)
