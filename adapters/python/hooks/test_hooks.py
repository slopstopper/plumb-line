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

# #493 (owner decision): a runner passes only by returning True. Anything else
# that is not False is an answer the gate cannot read, so it blocks, with the
# same reason as the JS twin.
@pytest.mark.parametrize("value", [1, "ok", None, {}])
def test_pre_commit_blocks_a_runner_result_that_is_not_true_or_false(value):
    r = pre_commit_gate.decide(runners=[("tests", lambda: value)])
    assert r == {"allow": False,
                 "reason": "pre-commit blocked: tests returned a result that is not true or false"}

@pytest.mark.filterwarnings("error")
def test_pre_commit_blocks_an_async_runner_it_cannot_await():
    # An un-awaited coroutine is truthy, so this passed the gate (#493). The
    # gate closes it, so no "coroutine was never awaited" warning is left.
    import gc

    async def runner():
        return False

    r = pre_commit_gate.decide(runners=[("tests", runner)])
    gc.collect()
    assert r == {"allow": False,
                 "reason": "pre-commit blocked: tests returned an awaitable; "
                           "the Python gate runs synchronous runners only"}

def test_pre_commit_blocks_an_awaitable_that_is_not_a_coroutine():
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        r = pre_commit_gate.decide(runners=[("tests", loop.create_future)])
    finally:
        loop.close()
    assert r["allow"] is False and "returned an awaitable" in r["reason"]

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


# #471: the CLI rows in adapters/hook-cases.json pin the same rules end to end;
# these pin decide() for a caller that imports it. JS twin: the #471 cases in
# adapters/js/hooks/__tests__/boundary-guard.test.mjs.
@pytest.mark.parametrize("file_path", [None, "", 7])
def test_boundary_decide_blocks_with_no_file_path(file_path):
    r = boundary_guard.decide(file_path=file_path, import_path="src/ui/view.py", **LAYERS)
    assert r["allow"] is False
    assert r["reason"].startswith("blocked: no file path to judge.")


@pytest.mark.parametrize("import_path", [None, ""])
def test_boundary_decide_allows_with_no_import_to_judge(import_path):
    r = boundary_guard.decide(file_path="src/data/store.py", import_path=import_path, **LAYERS)
    assert r == {"allow": True, "reason": "no import to judge"}


def test_boundary_decide_blocks_an_import_path_that_is_not_a_string():
    r = boundary_guard.decide(file_path="src/data/store.py", import_path=7, **LAYERS)
    assert r["allow"] is False
    assert r["reason"].startswith("blocked: importPath must be a string.")


# #516: an import to judge with no layers blocks, for a caller of decide() as
# for the CLI. JS twin: the #516 cases in boundary-guard.test.mjs.
@pytest.mark.parametrize("layers", [None, [], ()])
def test_boundary_decide_blocks_with_no_layers(layers):
    r = boundary_guard.decide("src/data/store.py", "src/ui/view.py", layers)
    assert r == {"allow": False,
                 "reason": 'blocked: no layers configured, so this import cannot be judged. Set "layers" in '
                           "PLUMBLINE_CFG to the project's layer names, top to bottom."}


@pytest.mark.parametrize("layers", ["ui", 7, {"ui": 1}])
def test_boundary_decide_blocks_layers_that_are_not_a_list(layers):
    r = boundary_guard.decide("src/data/store.py", "src/ui/view.py", layers)
    assert r == {"allow": False, "reason": "blocked: layers must be a list of layer names."}


def test_boundary_decide_accepts_a_tuple_of_layers_as_a_list():
    # A tuple judged correctly before #516; Python keeps accepting it (JS has no tuple).
    r = boundary_guard.decide("src/data/store.py", "src/ui/view.py", ("ui", "engine", "services", "data"))
    assert r == {"allow": False, "reason": "boundary break: data must not import ui (downward)"}


def test_boundary_decide_with_no_layers_keeps_the_earlier_checks_first():
    assert boundary_guard.decide("", "src/ui/view.py", [])["reason"].startswith("blocked: no file path to judge.")
    assert boundary_guard.decide("src/x.py", "", []) == {"allow": True, "reason": "no import to judge"}
    assert boundary_guard.decide("src/x.py", 7, [])["reason"].startswith("blocked: importPath must be a string.")


# --- #471 re-review: with stderr closed (2>&-), sys.stderr is None. The
# UTF-8 reconfigure must not crash the hook (exit 1): an allowed edit still
# exits 0 and a blocked one exits 2, as in the JS twins. The shared table's
# runners cannot close a stream, so this is spawned through sh here.

@pytest.mark.parametrize("script,stdin,env,code", [
    ("branch_guard.py", '{"filePath": "src/app.py"}', {"PLUMBLINE_BRANCH": "feature/x"}, 0),
    ("branch_guard.py", '{"filePath": "src/app.py"}', {"PLUMBLINE_BRANCH": "main"}, 2),
    ("boundary_guard.py", '{"filePath": "src/ui/x.py"}', {}, 0),
    ("boundary_guard.py", "not json", {}, 2),
    # The gate needs the same handling (v0.11.5 dogfood): it exited 1 here.
    ("pre_commit_gate.py", "", {"PLUMBLINE_TEST_CMD": "true"}, 0),
    ("pre_commit_gate.py", "", {"PLUMBLINE_TEST_CMD": "false"}, 2),
    ("pre_commit_gate.py", "", {}, 2),
])
def test_hooks_exit_the_same_with_stderr_closed(script, stdin, env, code):
    import subprocess
    path = os.path.join(os.path.dirname(__file__), script)
    full_env = {k: v for k, v in os.environ.items() if not k.startswith("PLUMBLINE_")}
    full_env.update(env)
    r = subprocess.run(["sh", "-c", '"$0" "$1" 2>&-', sys.executable, path],
                       input=stdin, text=True, capture_output=False, env=full_env)
    assert r.returncode == code


# --- #501 review: under an 8-bit locale (e.g. ISO-8859-1), os.environ decodes
# every byte, so \xff arrives as "ÿ" and a valid "café" as "cafÃ©". The hooks
# must judge the environment's bytes, as the JS twin does, not the locale's
# reading of them. CI cannot rely on such a locale being installed, so this
# simulates one: os.environ holds the Latin-1 reading, os.environb the bytes.

def _latin1_environ(monkeypatch, name, raw):
    monkeypatch.setattr(os, "environ", {name: raw.decode("latin-1")})
    monkeypatch.setattr(os, "environb", {name.encode(): raw})


@pytest.mark.parametrize("module", [branch_guard, boundary_guard, pre_commit_gate])
def test_env_problem_reads_bytes_not_the_locale(monkeypatch, module):
    _latin1_environ(monkeypatch, "PLUMBLINE_X", b"main\xff")
    assert module._env_problem("PLUMBLINE_X").startswith("PLUMBLINE_X is not valid UTF-8")


@pytest.mark.parametrize("module", [branch_guard, boundary_guard, pre_commit_gate])
def test_env_value_is_the_bytes_read_as_utf8(monkeypatch, module):
    _latin1_environ(monkeypatch, "PLUMBLINE_X", "caf\u00e9".encode("utf-8"))
    assert module._env_problem("PLUMBLINE_X") is None
    assert module._env("PLUMBLINE_X") == "caf\u00e9"


def test_gate_passes_the_command_to_the_process_as_utf8_bytes(monkeypatch):
    # subprocess encodes str arguments by the locale; under an 8-bit one
    # "caf\u00e9" would reach the command as other bytes than the JS twin sends
    # (#501 re-review). On POSIX the gate passes the UTF-8 bytes itself.
    _latin1_environ(monkeypatch, "PLUMBLINE_TEST_CMD", "grep caf\u00e9".encode("utf-8"))
    seen = []

    class _Done:
        returncode = 0

    monkeypatch.setattr(pre_commit_gate.subprocess, "run", lambda argv: seen.append(argv) or _Done())
    assert pre_commit_gate._main()["allow"] is True
    assert seen == [[b"grep", "caf\u00e9".encode("utf-8")]]


def test_branch_guard_reads_its_branch_and_config_through_the_bytes(monkeypatch):
    # The value decide() judges is the bytes read as UTF-8, not the locale's
    # reading: "caf\u00e9" must match a protected "caf\u00e9" (#501 re-review).
    import json
    branch, cfg = "caf\u00e9".encode("utf-8"), json.dumps(
        {"protectedBranches": ["caf\u00e9"]}, ensure_ascii=False).encode("utf-8")
    monkeypatch.setattr(os, "environ", {"PLUMBLINE_BRANCH": branch.decode("latin-1"),
                                        "PLUMBLINE_CFG": cfg.decode("latin-1")})
    monkeypatch.setattr(os, "environb", {b"PLUMBLINE_BRANCH": branch, b"PLUMBLINE_CFG": cfg})
    monkeypatch.setattr(branch_guard, "_read_stdin", lambda: '{"filePath": "src/app.py"}')
    r = branch_guard._main()
    assert r["allow"] is False and "on protected branch caf\u00e9" in r["reason"]


@pytest.mark.parametrize("module", [branch_guard, boundary_guard, pre_commit_gate])
def test_env_problem_without_a_bytes_environment_blocks_a_lone_surrogate(monkeypatch, module):
    # Windows has no os.environb; a lone surrogate there is not UTF-8 either.
    monkeypatch.setattr(os, "supports_bytes_environ", False)
    monkeypatch.setattr(os, "environ", {"PLUMBLINE_X": "main\ud800"})
    assert module._env_problem("PLUMBLINE_X").startswith("PLUMBLINE_X is not valid UTF-8")


# --- v0.11.5 dogfood: a closed stdin (<&-) reads as empty in the Python
# guards, as in the JS twins: no file path, so exit 2.
@pytest.mark.parametrize("script", ["branch_guard.py", "boundary_guard.py"])
def test_guards_block_with_stdin_closed(script):
    import subprocess
    path = os.path.join(os.path.dirname(__file__), script)
    env = {k: v for k, v in os.environ.items() if not k.startswith("PLUMBLINE_")}
    env["PLUMBLINE_BRANCH"] = "main"
    r = subprocess.run(["sh", "-c", '"$0" "$1" <&-', sys.executable, path],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "no file path" in r.stderr


# --- #515: the branch guard's path rule is Node's path.posix.normalize, in
# both twins: a trailing slash is kept and "\\" is an ordinary character.
# Python used os.path.normpath (which strips a trailing slash) and then turned
# backslashes into "/", so it allowed paths the JS twin blocked. This checks
# the Python normaliser against Node itself on fixed and seeded paths.
def _seeded_paths(n):
    alphabet = ["a", "b", ".", "..", "/", "//", "\\", "docs", "\u00e9", " "]
    seed, out = 515, []
    for _ in range(n):
        parts = []
        for _ in range(1 + seed % 7):
            seed = (seed * 1103515245 + 12345) % 2 ** 31
            parts.append(alphabet[seed % len(alphabet)])
        out.append("".join(parts))
    return out


def test_normalize_path_matches_node_posix_normalize():
    import json
    import subprocess
    paths = ["", ".", "./", "..", "../", "/", "//", "///a", "/..", "a/..", "a/../", "a/./b/",
             "docs", "docs/.", "docs/", "README.md/", "docs\\x.md", "docs\\..\\src", "a//b",
             "../a/", "a/b/../../..", "/a/b/../../..", "\u00e9/./\u00e9/"] + _seeded_paths(400)
    node = subprocess.run(
        ["node", "-e", "const p=require('path');process.stdout.write(JSON.stringify("
                       "JSON.parse(require('fs').readFileSync(0,'utf8')).map((s)=>p.posix.normalize(s))))"],
        input=json.dumps(paths), capture_output=True, text=True, check=True)
    expected = json.loads(node.stdout)
    got = [branch_guard._normalize_path(p) for p in paths]
    assert [(p, g, e) for p, g, e in zip(paths, got, expected) if g != e] == []
