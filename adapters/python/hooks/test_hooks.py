import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import branch_guard
import boundary_guard
import pre_commit_gate
import pytest

CFG = {"protected_branches": ["main"], "docs_allowlist": ["docs/", "README.md"]}

def test_branch_blocks_code_on_protected():
    r = branch_guard.decide(file_path="src/app.py", branch="main", **CFG)
    assert r["allow"] is False

def test_branch_allows_docs_on_protected():
    r = branch_guard.decide(file_path="docs/x.md", branch="main", **CFG)
    assert r["allow"] is True

def test_branch_allows_feature_branch():
    r = branch_guard.decide(file_path="src/app.py", branch="feature/x", **CFG)
    assert r["allow"] is True

def test_branch_blocks_upward_escaping_path_on_protected():
    r = branch_guard.decide(file_path="../secret.py", branch="main", **CFG)
    assert r["allow"] is False
    assert "protected branch" in r["reason"]

def test_branch_blocks_path_traversal_through_docs_directory_entry():
    r = branch_guard.decide(
        file_path="docs/../src/app.py",
        branch="main",
        protected_branches=["main"],
        docs_allowlist=["docs/", "README.md"],
    )
    assert r["allow"] is False

def test_branch_blocks_file_with_allowlist_entry_as_prefix():
    r = branch_guard.decide(
        file_path="README.md.bak",
        branch="main",
        protected_branches=["main"],
        docs_allowlist=["README.md"],
    )
    assert r["allow"] is False

def test_branch_allows_extension_glob_at_any_depth():
    glob_cfg = {"protected_branches": ["main"], "docs_allowlist": ["*.md"]}
    assert branch_guard.decide(file_path="README.md", branch="main", **glob_cfg)["allow"] is True
    assert branch_guard.decide(file_path="docs/guide/intro.md", branch="main", **glob_cfg)["allow"] is True

def test_branch_blocks_non_matching_extension_glob():
    glob_cfg = {"protected_branches": ["main"], "docs_allowlist": ["*.md"]}
    assert branch_guard.decide(file_path="src/app.py", branch="main", **glob_cfg)["allow"] is False
    # Name contains the extension chars but does not end in ".md".
    assert branch_guard.decide(file_path="src/amd.py", branch="main", **glob_cfg)["allow"] is False

def test_branch_raises_on_empty_allowlist_entry():
    with pytest.raises(ValueError, match="docs_allowlist must not contain empty entries"):
        branch_guard.decide(
            file_path="src/app.py",
            branch="main",
            protected_branches=["main"],
            docs_allowlist=[""],
        )

LAYERS = {"layers": ["ui", "engine", "services", "data"], "direction": "downward"}

def test_boundary_blocks_upward_import():
    r = boundary_guard.decide(file_path="src/data/store.py", import_path="src/ui/view.py", **LAYERS)
    assert r["allow"] is False

def test_boundary_allows_downward_import():
    r = boundary_guard.decide(file_path="src/ui/view.py", import_path="src/engine/calc.py", **LAYERS)
    assert r["allow"] is True

def test_pre_commit_blocks_on_failure():
    r = pre_commit_gate.decide(runners=[("tests", lambda: False)])
    assert r["allow"] is False

def test_pre_commit_allows_when_all_runners_pass():
    r = pre_commit_gate.decide(runners=[("tests", lambda: True), ("lint", lambda: True)])
    assert r["allow"] is True
    assert r["reason"] == "all gates passed"

# #476: a gate that ran nothing must not report that everything passed.
# Every way of not running the tests blocks (#467), in both twins.
def test_pre_commit_blocks_when_there_are_no_runners():
    r = pre_commit_gate.decide(runners=[])
    assert r == {"allow": False, "reason": "pre-commit blocked: no gates configured"}

def test_pre_commit_reads_a_generator_of_runners_lazily_stopping_at_the_first_failure():
    order = []

    def runners():
        order.append("y1")
        yield ("tests", lambda: order.append("tests") or False)
        order.append("y2")
        yield ("lint", lambda: True)

    assert pre_commit_gate.decide(runners=runners())["allow"] is False
    assert order == ["y1", "tests"]

def test_pre_commit_blocks_when_the_runners_are_an_empty_generator():
    r = pre_commit_gate.decide(runners=(x for x in ()))
    assert r == {"allow": False, "reason": "pre-commit blocked: no gates configured"}

def test_boundary_allows_same_layer_import():
    # importPath resolves to the same layer as filePath — exercises the src == dst branch.
    r = boundary_guard.decide(
        file_path="src/engine/a.py",
        import_path="src/engine/b.py",
        **LAYERS,
    )
    assert r["allow"] is True
    assert r["reason"] == "same or unscoped layer"

def test_boundary_layer_metachar_matched_literally():
    # Layer "a.b" must match only literal "a.b" path segments, not "axb".
    meta_layers = {"layers": ["a.b", "engine"], "direction": "downward"}
    no_match = boundary_guard.decide(
        file_path="src/axb/thing.py",
        import_path="src/engine/calc.py",
        **meta_layers,
    )
    # "axb" does not contain the literal layer "a.b" → filePath is unscoped → allow
    assert no_match["allow"] is True
    assert no_match["reason"] == "same or unscoped layer"

    exact_match = boundary_guard.decide(
        file_path="src/a.b/thing.py",
        import_path="src/engine/calc.py",
        **meta_layers,
    )
    # "a.b" is index 0, "engine" is index 1 → downward → allow
    assert exact_match["allow"] is True
    assert "respects downward" in exact_match["reason"]

def test_gate_blocks_on_untagged_output(tmp_path):
    import provenance_lint as pl
    src_file = tmp_path / "m.py"
    src_file.write_text("from plumb_line_provenance import mark, derive\n"
                        "def f(x, r):\n    return x * r\n")
    def lint_runner():
        return pl.main(['--require-output', str(src_file)]) == 0
    r = pre_commit_gate.decide(runners=[("require-provenance-output", lint_runner)])
    assert r["allow"] is False
    assert "require-provenance-output" in r["reason"]


# --- #449: "branch unknown" is an inconclusive result, never a pass. A code
# edit's answer depends on the branch, so it blocks; a docs-allowlisted edit is
# allowed on every branch, so it stays allowed.

@pytest.mark.parametrize("branch", [None, "", "  "])
def test_branch_blocks_code_when_the_branch_is_unknown(branch):
    r = branch_guard.decide(file_path="src/app.py", branch=branch, **CFG)
    assert r["allow"] is False and "branch unknown" in r["reason"]


def test_branch_allows_docs_when_the_branch_is_unknown():
    assert branch_guard.decide(file_path="docs/x.md", branch=None, **CFG)["allow"] is True


def test_branch_blocks_an_upward_escape_when_the_branch_is_unknown():
    r = branch_guard.decide(file_path="../docs/x.md", branch="", **CFG)
    assert r["allow"] is False and "branch unknown" in r["reason"]


# --- #449 review: a missing or non-string filePath (an unmapped host payload)
# must block wherever the branch matters.

@pytest.mark.parametrize("file_path", [None, 5, ""])
def test_branch_blocks_when_there_is_no_file_path_on_a_protected_branch(file_path):
    r = branch_guard.decide(file_path=file_path, branch="main", **CFG)
    assert r["allow"] is False and "no file path" in r["reason"]


def test_branch_blocks_when_there_is_no_file_path_and_the_branch_is_unknown():
    assert branch_guard.decide(file_path=None, branch=None, **CFG)["allow"] is False


def test_branch_allows_no_file_path_on_an_unprotected_branch():
    assert branch_guard.decide(file_path=None, branch="feature/x", **CFG)["allow"] is True


@pytest.mark.parametrize("branch", ["\ufeff", "\x85"])
def test_branch_blank_means_ascii_whitespace_as_in_the_js_twin(branch):
    assert branch_guard.decide(file_path="src/app.py", branch=branch, **CFG)["allow"] is True


# --- CLI behaviour is in adapters/hook-cases.json, run against both twins by
# test_hook_cases.py (#475), including quoting in PLUMBLINE_TEST_CMD (#472).
