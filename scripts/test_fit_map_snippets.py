"""test_fit_map_snippets — executes the Python snippets in reference/fit-map.md
against primitives/python, so the canonical examples cannot rot as the API
moves (GH #262, filed from the PR #261 review that caught three broken
snippets by running them).

Run from the repo root:

    python3 -m pytest -q scripts/test_fit_map_snippets.py

Mirrors the scripts/test_bundle_conformance.py precedent: repo-infrastructure
suite living outside any package. The primitive is loaded from
primitives/python under its published import name (`plumb_line_provenance`)
so the snippets run exactly as written for a consumer.

Each snippet's free names (the surrounding code a doc snippet elides) are
supplied by a per-snippet prelude below, keyed by a marker string unique to
that snippet. A snippet with no matching prelude, or a prelude whose marker no
longer matches — or a fence tag the extractor does not recognize — fails the
suite: additions, removals and renames in the fit-map must be mirrored here,
loudly.
"""
import importlib.util
import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIT_MAP = os.path.join(_ROOT, 'reference', 'fit-map.md')
_PKG_DIR = os.path.join(_ROOT, 'primitives', 'python')

# Load primitives/python as a real package under its published name, so the
# snippets' `from plumb_line_provenance... import ...` lines run verbatim.
if 'plumb_line_provenance' not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        'plumb_line_provenance', os.path.join(_PKG_DIR, '__init__.py'),
        submodule_search_locations=[_PKG_DIR])
    _pkg = importlib.util.module_from_spec(_spec)
    sys.modules['plumb_line_provenance'] = _pkg
    _spec.loader.exec_module(_pkg)

# If some earlier import in this process planted a different copy (an
# installed distribution, a sibling suite), we would silently test the wrong
# code — assert the loaded copy is the repo's, never assume it.
assert sys.modules['plumb_line_provenance'].__file__.startswith(_PKG_DIR), (
    'plumb_line_provenance resolved outside primitives/python: '
    + str(sys.modules['plumb_line_provenance'].__file__))

# Fence tags this suite understands. ```python runs here; ```js runs in the
# JS twin (primitives/js/fit-map-snippets.test.mjs, GH #265). Any OTHER tag
# (```py, ```python3, an info-string suffix) fails test_no_unrecognized_fences
# instead of silently escaping both guards.
_RUN_TAGS = {'python'}
_GUARDED_ELSEWHERE_TAGS = {'js'}


def _extract_blocks(text):
    """Return (tag, body) for every fenced code block, in order."""
    return re.findall(r'```([^\n]*)\n(.*?)```', text, re.DOTALL)


with open(_FIT_MAP) as f:
    _TEXT = f.read()
ALL_BLOCKS = _extract_blocks(_TEXT)
BLOCKS = [body for tag, body in ALL_BLOCKS if tag.strip() in _RUN_TAGS]


def _run_snippet(block, ns, name='fit-map.md'):
    """The one exec path every snippet goes through (also used by the
    harness self-test, so the pipeline itself is what is pinned)."""
    exec(compile(block, name, 'exec'), ns)  # noqa: S102
    return ns


def _fresh_response():
    """A real requests.Response (tag_requests type-checks isinstance), built
    offline — no network in this suite."""
    requests = pytest.importorskip('requests')
    r = requests.models.Response()
    r.status_code = 200
    r._content = b'{"a": 1}'
    return r


class _Template:
    def format(self, r):
        return f'[{r}]'


# marker (unique structural substring of the snippet) -> (free names,
# postcondition). The postcondition receives the snippet's namespace after
# exec and asserts the behavior the surrounding prose claims.
def _check_profile1(ns):
    # Prelude runs the snippet on the fallback path (ok=False): taint must be
    # carried, as the snippet's comment claims. The real branch is exercised
    # separately in test_profile1_real_branch.
    from plumb_line_provenance import meta_of
    assert meta_of(ns['rendered'])['derived_from_mock'] is True


def _check_profile2(ns):
    from plumb_line_provenance import meta_of
    assert ns['problems'] == []
    assert meta_of(ns['merged'])['confidence'] == 'low'


def _check_profile3(ns):
    combined = ns['combined']
    # The snippet's comments claim both: taint recorded, audit clean.
    assert combined.meta['derived_from_mock'] is True
    assert combined.audit() == []


def _check_profile4(ns):
    assert ns['env']['meta']['source'] == 'real'
    assert ns['env']['meta']['confidence'] == 'high'


def _profile1_names(ok):
    return {'ok': ok, 'completion': 'real completion',
            'FALLBACK_TEXT': 'canned', 'template': _Template()}


PRELUDES = {
    'FALLBACK_TEXT': (lambda: _profile1_names(ok=False), _check_profile1),
    'basis="agent run': (
        lambda: (lambda m: {'agent_row': {'a': 1},
                            'verified': m.mark({'b': 2}, source='real',
                                               confidence='high'),
                            'combine_rows': lambda a, b: {**a, **b}}
                 )(sys.modules['plumb_line_provenance']),
        _check_profile2,
    ),
    'plumb_concat': (
        lambda: (lambda pd: {'load_feed': lambda: pd.DataFrame({'x': [1]}),
                             'load_fixture': lambda: pd.DataFrame({'x': [9]})}
                 )(pytest.importorskip('pandas')),
        _check_profile3,
    ),
    'tag_requests': (
        lambda: {'requests': type('R', (), {'get': staticmethod(
            lambda url: _fresh_response())}), 'url': 'https://example.test'},
        _check_profile4,
    ),
}


def test_no_unrecognized_fences():
    # A ```py / ```python3 / info-string fence would otherwise be invisible
    # to the extractor — a snippet (broken or not) escaping the guard is the
    # drift class this suite exists to exclude.
    tags = {tag.strip() for tag, _ in ALL_BLOCKS}
    unknown = tags - _RUN_TAGS - _GUARDED_ELSEWHERE_TAGS
    assert not unknown, (
        f'fit-map has fence tag(s) {sorted(unknown)!r} the snippet guard '
        f'does not recognize — add to _RUN_TAGS (and a prelude) or to '
        f'_GUARDED_ELSEWHERE_TAGS (and a twin guard), never let a fence '
        f'escape silently')


def test_extraction_found_the_snippets():
    # The #249 lesson: a run that finds nothing must not look like a run that
    # verified everything. Every prelude marker must match exactly one block.
    assert len(BLOCKS) >= len(PRELUDES), (
        f'only {len(BLOCKS)} python blocks extracted from {_FIT_MAP}')
    for marker in PRELUDES:
        hits = [b for b in BLOCKS if marker in b]
        assert len(hits) == 1, (
            f'marker {marker!r} matched {len(hits)} snippets — fit-map and '
            f'preludes have drifted; update PRELUDES to match the doc')


def test_every_python_block_has_a_prelude():
    # A new snippet added to the fit-map without a prelude here would
    # otherwise run in no test at all.
    for block in BLOCKS:
        assert any(marker in block for marker in PRELUDES), (
            'fit-map python snippet has no matching prelude — add one:\n'
            + block)


@pytest.mark.parametrize('marker', sorted(PRELUDES))
def test_snippet_executes_and_behaves(marker):
    block = next((b for b in BLOCKS if marker in b), None)
    assert block is not None, (
        f'marker {marker!r} matches no snippet — fit-map and preludes have '
        f'drifted; update PRELUDES to match the doc')
    make_ns, check = PRELUDES[marker]
    ns = _run_snippet(block, make_ns(), f'fit-map.md[{marker}]')
    check(ns)


def test_profile1_real_branch():
    # The snippet is a conditional expression; the parametrized run takes the
    # fallback path only. Execute the same block with ok=True so a defect in
    # the real branch (the pre-#261 class: a wrong kwarg) cannot hide behind
    # lazy evaluation.
    from plumb_line_provenance import meta_of
    block = next((b for b in BLOCKS if 'FALLBACK_TEXT' in b), None)
    assert block is not None, 'profile 1 snippet not found'
    ns = _run_snippet(block, _profile1_names(ok=True), 'fit-map.md[real]')
    assert meta_of(ns['rendered'])['derived_from_mock'] is False


def test_harness_catches_a_broken_snippet():
    # Self-test through the same pipeline the real snippets use: a
    # known-broken block (the pre-fix profile-2 bug verbatim) must raise out
    # of _run_snippet, proving the guard's failure mode is loud.
    broken = ("from plumb_line_provenance import mark\n"
              "mark({'v': 1}, provenance='not a real kwarg')\n")
    with pytest.raises(TypeError):
        _run_snippet(broken, {}, 'fit-map.md[broken]')
