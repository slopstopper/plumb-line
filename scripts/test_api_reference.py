"""docs/api.md documents the user-facing API the packages actually export (#445).

The page claimed to document every export and had drifted: validateEnvelope,
stepId, the baseline API and the Python dataframe wrappers were missing. The
export lists here come from the modules themselves, so a new public name
fails this suite until api.md gains a heading for it.

Run from the repo root: python3 -m pytest -q scripts/test_api_reference.py
"""
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JS = os.path.join(_ROOT, "primitives", "js")
_PY = os.path.join(_ROOT, "primitives", "python")

with open(os.path.join(_ROOT, "docs", "api.md"), encoding="utf-8") as fh:
    API = fh.read()

# Every backticked identifier in a heading line: what the page documents.
HEADING_NAMES = {n for line in API.split("\n") if line.startswith("#")
                 for span in re.findall(r"`([^`]+)`", line)
                 for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", span)}

# The user-facing baseline calls. baseline.mjs also exports internal helpers
# (canonicalJson, deepEqual, ...) for its tests; api.md says so and does not
# document them as API (the API surface is decided at v1.0.0, #236).
JS_BASELINE_API = {"check", "assertBaseline", "update", "list", "show", "validateBaseline"}
TEST_ONLY = {"__resetStepCounter"}


def _js_exports(module):
    out = subprocess.run(
        ["node", "--input-type=module", "-e",
         f'console.log(JSON.stringify(Object.keys(await import("./{module}"))))'],
        cwd=_JS, capture_output=True, text=True, check=True)
    return set(json.loads(out.stdout))


def _py_package():
    spec = importlib.util.spec_from_file_location(
        "plumb_line_provenance", os.path.join(_PY, "__init__.py"), submodule_search_locations=[_PY])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("plumb_line_provenance", pkg)
    if sys.modules["plumb_line_provenance"] is pkg:
        spec.loader.exec_module(pkg)
    return sys.modules["plumb_line_provenance"]


def _py_public(modname):
    mod = importlib.import_module(f"plumb_line_provenance.{modname}")
    return {n for n in dir(mod) if not n.startswith("_") and callable(getattr(mod, n))
            and getattr(getattr(mod, n), "__module__", "") == mod.__name__} - {"main"}


def _required():
    names = (_js_exports("index.mjs") - TEST_ONLY) | _js_exports("http.mjs") | JS_BASELINE_API
    pkg = _py_package()
    names |= set(pkg.__all__)
    for mod in ("http_adapter", "frames", "arrays"):
        names |= _py_public(mod)
    return names


def test_every_user_facing_export_has_a_heading():
    missing = sorted(_required() - HEADING_NAMES)
    assert not missing, f"docs/api.md has no heading for: {missing}"


def test_the_page_scopes_its_claim():
    # It documents the user-facing API; it must not claim "every" export while
    # baseline.mjs exports internal helpers it deliberately leaves out.
    assert "every function and constant exported" not in API


@pytest.mark.parametrize("anchor", sorted(set(re.findall(r"\]\(#([^)]+)\)", API))))
def test_in_page_anchors_resolve(anchor):
    def slug(h):
        h = h.strip().lstrip("#").strip().lower()
        h = re.sub(r"[^\w\- ]", "", h)
        return h.replace(" ", "-")
    slugs = {slug(line) for line in API.split("\n") if line.startswith("#")}
    assert anchor in slugs, f"#{anchor} matches no heading"


def test_status_ladder_matches_the_code():
    out = subprocess.run(["node", "--input-type=module", "-e",
                          'import {STATUS} from "./index.mjs"; console.log(JSON.stringify(STATUS))'],
                         cwd=_JS, capture_output=True, text=True, check=True)
    ladder = " < ".join(f"`{s}`" for s in json.loads(out.stdout))
    assert ladder in API, f"api.md should state the STATUS order {ladder}"
