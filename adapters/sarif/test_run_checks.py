"""Tests for adapters/sarif/run_checks.py — the Action's orchestrator (#118).

Run from the repo root:  python3 -m pytest -q adapters/sarif
The fake runner makes every tool's behaviour explicit; the last test runs the
real tools over the planted fixtures.
"""
import json
import os
import shutil

from adapters.sarif import ratchet as RT
from adapters.sarif import run_checks as R

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _consumer(tmp_path, manifest):
    root = tmp_path / "repo"
    (root / ".plumb-line").mkdir(parents=True)
    for f in ("eslint-boundary.cjs", "eslint-provenance.cjs", ".importlinter"):
        (root / f).write_text("x\n", encoding="utf-8")
    (root / ".plumb-line" / "baselines").mkdir()
    (root / ".plumb-line" / "enforcement.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "src" / "p").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "p" / "b.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "a.js").write_text("export const x = 1;\n", encoding="utf-8")
    (root / "src" / "p" / "b.js").write_text("export const x = 1;\n", encoding="utf-8")
    return str(root)


FULL = {"enforcement-format": "v1", "languages": ["js", "python"],
        "js": {"boundary": {"config": "eslint-boundary.cjs"},
               "provenance": {"config": "eslint-provenance.cjs", "globs": ["src/**/*.js"], "outputGlobs": ["src/p/**/*.js"]}},
        "python": {"boundary": {"config": ".importlinter"},
                   "provenance": {"globs": ["src/**/*.py"], "outputGlobs": ["src/p/**/*.py"]}},
        "baselines": {"dir": ".plumb-line/baselines"}}


class FakeRunner:
    """Answers each COMMAND, not merely each tool. The base key is whichever
    token in cmd names the tool itself — a .py/.mjs script path, or a bare
    "eslint"/"lint-imports" — falling back to cmd[0]; it is then narrowed by
    what that command was asked to do, because one binary serves several
    capabilities:

        "provenance_lint.py"          python.provenance
        "provenance_lint.py:output"   python.output  (--require-output; the
                                      real main() swaps in a different check
                                      entirely on that flag, so
                                      python.provenance can never emit
                                      REQ-OUTPUT)
        "eslint:."                    js.boundary    (lints the root)
        "eslint:src/**/*.js"          js.provenance  (its globs)
        "eslint:src/p/**/*.js"        js.output      (its outputGlobs)

    The narrowed key wins; the bare tool token is the fallback, so a test
    that does not care answers "eslint" once. Records calls."""
    def __init__(self, answers, missing=()):
        self.answers, self.missing, self.calls = answers, set(missing), []

    def which(self, tool):
        return None if tool in self.missing else f"/usr/bin/{tool}"

    def _keys(self, cmd):
        tool = next((os.path.basename(a) for a in cmd if a.endswith((".py", ".mjs")) or a in ("eslint", "lint-imports")),
                    os.path.basename(cmd[0]))
        if "--require-output" in cmd:
            yield tool + ":output"
        elif tool == "eslint" and "--no-error-on-unmatched-pattern" in cmd:
            for target in cmd[cmd.index("--no-error-on-unmatched-pattern") + 1:]:
                yield f"{tool}:{target}"
        yield tool

    def __call__(self, cmd, cwd):
        self.calls.append((cmd, cwd))
        return next((self.answers[k] for k in self._keys(cmd) if k in self.answers), (0, "[]", ""))


def _paths(tmp_path):
    return {"sarif_path": str(tmp_path / "out.sarif"), "summary_path": str(tmp_path / "summary.json"),
            "step_summary_path": str(tmp_path / "step.md")}


def test_missing_manifest_fails_naming_the_bootstrap_step(tmp_path, capsys):
    root = str(tmp_path)
    os.makedirs(root, exist_ok=True)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=FakeRunner({}), version="t", **_paths(tmp_path))
    out = capsys.readouterr().out
    assert code == 1 and "manifest not found" in out and "bootstrap" in out and "enforcement-format" in out


def test_invalid_manifest_fails_with_findings_not_as_missing(tmp_path, capsys):
    root = _consumer(tmp_path, dict(FULL, **{"enforcement-format": "v9"}))
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=FakeRunner({}), version="t", **_paths(tmp_path))
    out = capsys.readouterr().out
    assert code == 1 and "unknown enforcement-format" in out and "manifest not found" not in out


def test_zero_capabilities_is_green_and_says_so(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"], "js": {}})
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=FakeRunner({}), version="t", **p)
    assert code == 0
    s = json.load(open(p["summary_path"]))
    assert s["capabilities"] == {} and s["findings"] == 0
    assert "0 checks ran" in open(p["step_summary_path"]).read()
    assert json.load(open(p["sarif_path"]))["runs"][0]["results"] == []


def test_all_capabilities_run_with_the_right_commands(tmp_path):
    root = _consumer(tmp_path, FULL)
    fake = FakeRunner({"eslint": (0, "[]", ""), "provenance_lint.py": (0, "[]", ""),
                       "lint-imports": (0, "Contracts: 1 kept, 0 broken.\n", ""),
                       "baseline-cli.mjs": (0, json.dumps({"dir": root, "files": [], "invalid": 0}), "")})
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=fake, version="t", **p)
    assert code == 0
    s = json.load(open(p["summary_path"]))
    assert {k: v["state"] for k, v in s["capabilities"].items()} == {
        "js.boundary": "ran", "js.provenance": "ran", "js.output": "ran",
        "python.boundary": "ran", "python.provenance": "ran", "python.output": "ran", "baselines": "ran"}
    cmds = [" ".join(c) for c, _ in fake.calls]
    assert any("eslint" in c and "eslint-boundary.cjs" in c and "--format json" in c for c in cmds)
    # M13: an ESLint glob that matches nothing is `ran` + zero results, like the Python side.
    assert all("--no-error-on-unmatched-pattern" in c for c in cmds if "eslint" in c)
    assert any("provenance_lint.py" in c and "--json" in c and "--require-output" not in c for c in cmds)
    assert any("provenance_lint.py" in c and "--require-output" in c and "--json" in c for c in cmds)
    assert any("lint-imports" in c and "--config .importlinter" in c for c in cmds)
    assert any("baseline-cli.mjs validate --json" in c for c in cmds)
    assert all(cwd == root for _, cwd in fake.calls)


def test_findings_fail_the_job_unless_fail_on_none(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["python"],
                                "python": {"provenance": {"globs": ["src/**/*.py"]}}})
    issue = [{"filename": "src/a.py", "line": 2, "rule": "PB1", "message": "PB1 laundered"}]
    fake = FakeRunner({"provenance_lint.py": (1, json.dumps(issue), "")})
    p = _paths(tmp_path)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    assert R.run(root, m, _ROOT, "findings", runner=fake, version="t", **p) == 1
    s = json.load(open(p["summary_path"]))
    assert s["findings"] == 1 and s["capabilities"]["python.provenance"]["results"] == 1
    assert json.load(open(p["sarif_path"]))["runs"][0]["results"][0]["ruleId"] == "PL/PB1"
    assert R.run(root, m, _ROOT, "none", runner=fake, version="t", **p) == 0
    assert "fail-on: none" in open(p["step_summary_path"]).read()


def test_missing_tool_is_a_finding_and_a_failure(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["python"],
                                "python": {"boundary": {"config": ".importlinter"}}})
    fake = FakeRunner({}, missing=("lint-imports",))
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=fake, version="t", **p)
    assert code == 1
    s = json.load(open(p["summary_path"]))
    assert s["capabilities"]["python.boundary"]["state"] == "tool-missing"
    assert "pip install import-linter==2.15" in s["capabilities"]["python.boundary"]["note"]
    res = json.load(open(p["sarif_path"]))["runs"][0]["results"]
    assert res[0]["ruleId"] == "PL/tool-missing"


def test_tool_crash_is_errored_with_stderr_in_the_note(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["python"],
                                "python": {"provenance": {"globs": ["src/**/*.py"]}}})
    fake = FakeRunner({"provenance_lint.py": (3, "", "Traceback: boom")})
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=fake, version="t", **p)
    assert code == 1
    s = json.load(open(p["summary_path"]))
    assert s["capabilities"]["python.provenance"]["state"] == "errored"
    assert "exit 3" in s["capabilities"]["python.provenance"]["note"] and "boom" in s["capabilities"]["python.provenance"]["note"]


def test_tool_exit_nonzero_with_parsable_output_is_findings_not_errored(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["python"],
                                "python": {"boundary": {"config": ".importlinter"}}})
    report = "Contracts: 0 kept, 1 broken.\nBroken contracts\n----------------\nsrc.data is not allowed to import src.ui:\n- src.data.schema -> src.ui.report (l.7)\n"
    fake = FakeRunner({"lint-imports": (1, report, "")})
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=fake, version="t", **p)
    s = json.load(open(p["summary_path"]))
    assert code == 1 and s["capabilities"]["python.boundary"]["state"] == "ran"
    assert s["capabilities"]["python.boundary"]["parser"] == "text" and s["findings"] == 1


# ---------- fix round 1 (task review) ----------

def test_parsable_payload_with_one_unmappable_item_is_ran_not_errored(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"],
                                "js": {"boundary": {"config": "eslint-boundary.cjs"}}})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "a.js"),
                           "messages": [{"ruleId": "no-unused-vars", "severity": 2, "message": "x",
                                        "line": 1, "column": 1}]}])
    fake = FakeRunner({"eslint": (1, payload, "")})
    p = _paths(tmp_path)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    assert R.run(root, m, _ROOT, "findings", runner=fake, version="t", **p) == 1
    s = json.load(open(p["summary_path"]))
    res = json.load(open(p["sarif_path"]))["runs"][0]["results"]
    assert (s["capabilities"]["js.boundary"]["state"] == "ran" and len(res) == 1
            and res[0]["ruleId"] == "PL/unparsed"
            and res[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/a.js")
    assert R.run(root, m, _ROOT, "none", runner=fake, version="t", **p) == 0


def test_tool_missing_and_errored_fail_even_under_fail_on_none(tmp_path):
    missing_root = _consumer(tmp_path / "missing", {"enforcement-format": "v1", "languages": ["python"],
                                                     "python": {"boundary": {"config": ".importlinter"}}})
    missing_code = R.run(missing_root, os.path.join(missing_root, ".plumb-line", "enforcement.json"), _ROOT, "none",
                         runner=FakeRunner({}, missing=("lint-imports",)), version="t",
                         **_paths(tmp_path / "missing"))
    crash_root = _consumer(tmp_path / "crash", {"enforcement-format": "v1", "languages": ["python"],
                                                "python": {"provenance": {"globs": ["src/**/*.py"]}}})
    crash_code = R.run(crash_root, os.path.join(crash_root, ".plumb-line", "enforcement.json"), _ROOT, "none",
                       runner=FakeRunner({"provenance_lint.py": (3, "", "Traceback: boom")}), version="t",
                       **_paths(tmp_path / "crash"))
    assert missing_code == 1 and crash_code == 1


def test_js_provenance_and_output_filter_by_rule(tmp_path):
    # js.boundary is enabled too, and answered on its own key ("eslint:." —
    # it lints the root, not globs). Without that separation boundary's
    # invocation would replay the payload below unfiltered and double every
    # count, so "exactly one of each" would be an artifact of the fake
    # rather than the capability filters under test.
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"], "js": FULL["js"]})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"),
                           "messages": [{"ruleId": "plumb-line/no-provenance-bypass",
                                        "message": "PB1 laundered", "line": 1, "column": 1},
                                       {"ruleId": "plumb-line/require-provenance-output",
                                        "message": "untagged output [site: f]", "line": 2, "column": 1}]}])
    clean = json.dumps([{"filePath": os.path.join(root, "src", "a.js"), "messages": []}])
    fake = FakeRunner({"eslint:.": (0, clean, ""), "eslint": (0, payload, "")})
    p = _paths(tmp_path)
    R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
         runner=fake, version="t", **p)
    s = json.load(open(p["summary_path"]))
    ids = [r["ruleId"] for r in json.load(open(p["sarif_path"]))["runs"][0]["results"]]
    assert (s["capabilities"]["js.provenance"]["results"] == 1 and s["capabilities"]["js.output"]["results"] == 1
            and ids.count("PL/PB1") == 1 and ids.count("PL/untagged-output") == 1)


def test_no_glob_match_is_ran_with_a_note_and_no_tool_call(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["python"],
                                "python": {"provenance": {"globs": ["nothing/**/*.py"]}}})
    issue = [{"filename": "x", "line": 1, "rule": "PB1", "message": "m"}]
    fake = FakeRunner({"provenance_lint.py": (1, json.dumps(issue), "")})
    p = _paths(tmp_path)
    R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
         runner=fake, version="t", **p)
    s = json.load(open(p["summary_path"]))
    assert (s["capabilities"]["python.provenance"]["state"] == "ran"
            and s["capabilities"]["python.provenance"]["note"] == "no files matched the globs"
            and not any("provenance_lint.py" in " ".join(c) for c, _ in fake.calls))


def test_step_summary_is_appended_not_overwritten(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"], "js": {}})
    p = _paths(tmp_path)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    R.run(root, m, _ROOT, "findings", runner=FakeRunner({}), version="t", **p)
    R.run(root, m, _ROOT, "findings", runner=FakeRunner({}), version="t", **p)
    headers = [ln for ln in open(p["step_summary_path"]).read().splitlines()
              if ln.startswith("plumb-line enforcement —")]
    assert len(headers) == 2


# ---------- final review I2: js.output keeps PL/unparsed ----------

def test_js_output_keeps_unparsed_for_a_surface_file_eslint_could_not_parse(tmp_path):
    # A file inside the declared surface that ESLint could not parse (a
    # fatal message, ruleId null) means require-provenance-output never ran
    # on it. Dropping PL/unparsed here was the one silent-green path left.
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"],
                                "js": {"provenance": {"config": "eslint-provenance.cjs",
                                                      "globs": ["src/**/*.js"], "outputGlobs": ["src/p/**/*.js"]}}})
    fatal = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"),
                         "messages": [{"ruleId": None, "fatal": True, "severity": 2,
                                      "message": "Parsing error: Unexpected token", "line": 1, "column": 8}]}])

    # The js.output run (outputGlobs) fails to parse; the js.provenance run
    # (globs) is clean — one binary, two commands, two answers.
    fake = FakeRunner({"eslint:src/p/**/*.js": (1, fatal, ""), "eslint": (0, "[]", "")})
    p = _paths(tmp_path)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    code = R.run(root, m, _ROOT, "findings", runner=fake, version="t", **p)
    s = json.load(open(p["summary_path"]))
    res = json.load(open(p["sarif_path"]))["runs"][0]["results"]
    assert s["capabilities"]["js.output"]["state"] == "ran" and s["capabilities"]["js.output"]["results"] == 1
    assert [r["ruleId"] for r in res] == ["PL/unparsed"] and "Parsing error" in res[0]["message"]["text"]
    assert res[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/p/b.js"
    assert code == 1


# ---------- final review I3 (+M13): the consumer's own ESLint, never npx ----------

class Recorder:
    """A runner with NO `which` hook, so run() falls back to its default
    resolver — the thing under test here. Every tool answers clean."""
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, cwd):
        self.calls.append((cmd, cwd))
        return (0, "[]", "")


def _plant_eslint(where):
    binary = where / "node_modules" / ".bin" / "eslint"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\necho []\n", encoding="utf-8")
    binary.chmod(0o755)
    return str(binary)


_JS_ONLY = {"enforcement-format": "v1", "languages": ["js"], "js": {"boundary": {"config": "eslint-boundary.cjs"}}}


def test_eslint_is_the_consumers_node_modules_binary(tmp_path):
    root = _consumer(tmp_path, _JS_ONLY)
    binary = _plant_eslint(tmp_path / "repo")
    rec = Recorder()
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=rec, version="t", **p)
    assert code == 0 and len(rec.calls) == 1
    cmd = rec.calls[0][0]
    assert cmd[0] == binary and "npx" not in cmd
    assert "--no-config-lookup" in cmd and "--no-error-on-unmatched-pattern" in cmd


def test_eslint_absent_from_node_modules_is_tool_missing_not_a_registry_install(tmp_path):
    root = _consumer(tmp_path, _JS_ONLY)
    rec = Recorder()
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=rec, version="t", **p)
    s = json.load(open(p["summary_path"]))
    assert code == 1 and rec.calls == []
    assert s["capabilities"]["js.boundary"]["state"] == "tool-missing"
    assert "npm ci" in s["capabilities"]["js.boundary"]["note"]
    assert json.load(open(p["sarif_path"]))["runs"][0]["results"][0]["ruleId"] == "PL/tool-missing"


def test_eslint_hoisted_above_a_monorepo_subroot_is_found_by_walking_up(tmp_path):
    root = _consumer(tmp_path / "packages", _JS_ONLY)   # <tmp>/packages/repo
    binary = _plant_eslint(tmp_path)                    # <tmp>/node_modules/.bin/eslint
    rec = Recorder()
    p = _paths(tmp_path)
    R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
          runner=rec, version="t", **p)
    assert rec.calls and rec.calls[0][0][0] == binary and rec.calls[0][1] == root


# ---------- final review I1 (+M1, M9): a subroot's results are workspace-relative ----------

def test_subroot_results_are_workspace_relative_and_srcroot_is_the_workspace(tmp_path):
    import pathlib
    # root = <tmp>/packages/repo, workspace = <tmp>: code scanning resolves
    # %SRCROOT% as the repository root, so a monorepo subroot's URIs must
    # carry the subroot prefix or every alert points at a path that isn't there.
    root = _consumer(tmp_path / "packages", {"enforcement-format": "v1", "languages": ["js"],
                                             "js": {"boundary": {"config": "eslint-boundary.cjs"}}})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "a.js"),
                           "messages": [{"ruleId": "import/no-restricted-paths", "severity": 2,
                                        "message": "up", "line": 1, "column": 1}]}])
    fake = FakeRunner({"eslint": (1, payload, "")})
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 runner=fake, version="t", workspace=str(tmp_path), **p)
    assert code == 1
    run = json.load(open(p["sarif_path"]))["runs"][0]
    uris = [r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for r in run["results"]]
    assert uris == ["packages/repo/src/a.js"]
    assert run["originalUriBaseIds"] == {"%SRCROOT%": {"uri": pathlib.Path(tmp_path).as_uri() + "/"}}
    assert all(cwd == root for _, cwd in fake.calls)  # the tools still run in the subroot


def test_workspace_defaults_to_root_so_uris_are_root_relative(tmp_path):
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"],
                                "js": {"boundary": {"config": "eslint-boundary.cjs"}}})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "a.js"),
                           "messages": [{"ruleId": "import/no-restricted-paths", "severity": 2,
                                        "message": "up", "line": 1, "column": 1}]}])
    p = _paths(tmp_path)
    R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
          runner=FakeRunner({"eslint": (1, payload, "")}), version="t", **p)
    run = json.load(open(p["sarif_path"]))["runs"][0]
    assert run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/a.js"
    assert run["originalUriBaseIds"]["%SRCROOT%"]["uri"].endswith("/repo/")


def test_main_realpaths_root_and_workspace_and_defaults_workspace_to_root(tmp_path, monkeypatch):
    # ESLint and node report the PHYSICAL cwd, so a symlinked --root (macOS
    # /var -> /private/var) must be resolved before _rel strips it (M9).
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    seen = {}

    def fake_run(root, manifest_path, scripts_dir, fail_on, sarif_path, summary_path,
                 step_summary_path=None, version="dev", runner=None, workspace=None):
        seen.update(root=root, manifest=manifest_path, workspace=workspace)
        return 0
    monkeypatch.setattr(R, "run", fake_run)
    R.main(["--root", str(link), "--sarif", str(tmp_path / "o.sarif"), "--summary", str(tmp_path / "s.json")])
    assert seen["root"] == os.path.realpath(str(real)) and seen["workspace"] == seen["root"]
    assert seen["manifest"] == os.path.join(seen["root"], ".plumb-line", "enforcement.json")
    ws_link = tmp_path / "ws-link"
    ws_link.symlink_to(tmp_path, target_is_directory=True)
    R.main(["--root", str(link), "--workspace", str(ws_link),
            "--sarif", str(tmp_path / "o.sarif"), "--summary", str(tmp_path / "s.json")])
    assert seen["workspace"] == os.path.realpath(str(tmp_path))


def test_end_to_end_over_the_planted_fixtures(tmp_path):
    """The only test that proves the mapping matches what the real tools emit.
    Skipped, loudly, if a tool is not installed locally — CI installs both."""
    import pytest
    missing = [t for t in ("node", "lint-imports") if shutil.which(t) is None]
    if missing:
        pytest.skip(f"real tools not installed locally: {missing}")
    # Each JS fixture needs the CONSUMER's own install: the boundary one needs
    # import-x, the ratchet one (#393) only ESLint itself — its config reaches
    # the plumb-line plugin by relative path.
    for fixture, mod in (("js-payments-service", "eslint-plugin-import-x"),
                         ("ratchet-adoption-js", "eslint")):
        for tree in ("broken", "clean"):
            if not os.path.isdir(os.path.join(_ROOT, "examples", fixture, tree, "node_modules", mod)):
                pytest.skip(f"JS fixture toolchain not installed: run npm ci in examples/{fixture}/{tree}")
    ratcheted = ("examples/ratchet-adoption", "examples/ratchet-adoption-js")
    for fixture, expect in (("examples/js-payments-service", {"PL/boundary"}),
                            ("examples/python-data-pipeline", {"PL/boundary"}),
                            ("examples/ratchet-adoption", {"PL/untagged-output"}),
                            ("examples/ratchet-adoption-js", {"PL/untagged-output"})):
        root = os.path.join(_ROOT, fixture, "broken")
        p = _paths(tmp_path / os.path.basename(fixture))
        os.makedirs(os.path.dirname(p["sarif_path"]), exist_ok=True)
        code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                     version="t", **p)
        assert code == 1, fixture
        ids = {r["ruleId"] for r in json.load(open(p["sarif_path"]))["runs"][0]["results"]}
        assert expect <= ids, (fixture, ids)
        if fixture in ratcheted:
            s = json.load(open(p["summary_path"]))
            assert (s["ratchet"]["known"], s["ratchet"]["new"], s["findings"]) == (1, 1, 1), s
            assert s["ratchet"]["unmeasured"] == [], s
        clean = os.path.join(_ROOT, fixture, "clean")
        code = R.run(clean, os.path.join(clean, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                     version="t", **p)
        assert code == 0, (fixture, open(p["step_summary_path"]).read())
        if fixture in ratcheted:
            s = json.load(open(p["summary_path"]))
            assert s["ratchet"] == {"file": ".plumb-line/ratchet.json", "state": "ran", "known": 2, "new": 0,
                                    "stale": 0, "unmeasured": []}, s
    # I1: run one fixture as a subroot of this checkout (the way ci.yml's
    # `root:` input does) — every located result must carry the subroot
    # prefix, so code scanning resolves it against the repository root.
    root = os.path.join(_ROOT, "examples", "js-payments-service", "broken")
    p = _paths(tmp_path / "subroot")
    os.makedirs(os.path.dirname(p["sarif_path"]), exist_ok=True)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                 version="t", workspace=_ROOT, **p)
    results = json.load(open(p["sarif_path"]))["runs"][0]["results"]
    uris = [r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for r in results if "locations" in r]
    assert code == 1 and uris and all(u.startswith("examples/js-payments-service/broken/") for u in uris), uris
    assert len(uris) == len(results), "every fixture result carries a location"


# ---------- #119 ratchet ----------

PY_OUT = {"enforcement-format": "v1", "languages": ["python"],
          "python": {"provenance": {"globs": ["src/**/*.py"], "outputGlobs": ["src/p/**/*.py"]}},
          "ratchet": {"file": ".plumb-line/ratchet.json"}}


def _untagged_issues(*sites):
    return json.dumps([{"filename": f, "line": 2, "rule": "REQ-OUTPUT", "symbol": s,
                        "message": "REQ-OUTPUT untagged output"} for f, s in sites])


def _ratchet(root, sites):
    d = RT.empty()
    d["sites"] = sites
    d["history"] = [{"date": "2026-09-15", "because": "initial pin", "change": "pinned"}]
    RT.write_ratchet(os.path.join(root, ".plumb-line", "ratchet.json"), d)


def _run(root, tmp_path, fake, fail_on="findings", **kw):
    p = _paths(tmp_path)
    code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, fail_on,
                 runner=fake, version="t", **p, **kw)
    return code, json.load(open(p["summary_path"])), json.load(open(p["sarif_path"])), open(p["step_summary_path"]).read()


def test_ratchet_known_is_a_note_new_is_an_error_and_only_new_fails(tmp_path):
    root = _consumer(tmp_path, PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::pinned"]})
    fake = FakeRunner({"provenance_lint.py": (0, "[]", ""),
                       "provenance_lint.py:output": (1, _untagged_issues(("src/p/b.py", "pinned"), ("src/p/b.py", "fresh")), "")})
    code, s, sarif, text = _run(root, tmp_path, fake)
    assert code == 1
    assert s["ratchet"] == {"file": ".plumb-line/ratchet.json", "state": "ran", "known": 1, "new": 1,
                            "stale": 0, "unmeasured": []}
    assert s["findings"] == 1 and s["notes"] == 1
    levels = {(r["message"]["text"][:16], r["level"]) for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/untagged-output"}
    assert ("known (ratchet):", "note") in levels
    assert "ratchet: 1 known, 1 new, 0 stale" in text.splitlines()[0]
    # Only the pinned site → green.
    _ratchet(root, {"python.output": ["src/p/b.py::fresh", "src/p/b.py::pinned"]})
    code, s, _, _ = _run(root, tmp_path, fake)
    assert code == 0 and s["findings"] == 0 and s["ratchet"]["known"] == 2


def test_ratchet_stale_is_a_note_that_never_fails(tmp_path):
    root = _consumer(tmp_path, PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::gone"]})
    ratchet_path = os.path.join(root, ".plumb-line", "ratchet.json")
    before = open(ratchet_path, "rb").read()
    fake = FakeRunner({"provenance_lint.py": (0, "[]", "")})
    code, s, sarif, _ = _run(root, tmp_path, fake)
    assert code == 0 and s["ratchet"]["stale"] == 1 and s["findings"] == 0
    stale = [r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/ratchet-stale"]
    assert len(stale) == 1 and stale[0]["level"] == "note" and "src/p/b.py::gone" in stale[0]["message"]["text"]
    # The runner is read-only: the ratchet file is byte-for-byte unchanged.
    assert open(ratchet_path, "rb").read() == before


def test_ratchet_missing_file_is_invalid_fails_and_runs_unratcheted(tmp_path):
    root = _consumer(tmp_path, PY_OUT)  # no ratchet file written
    fake = FakeRunner({"provenance_lint.py": (0, "[]", ""),
                       "provenance_lint.py:output": (1, _untagged_issues(("src/p/b.py", "x")), "")})
    code, s, sarif, text = _run(root, tmp_path, fake, fail_on="none")
    assert code == 1, "fails even under fail-on: none, like tool-missing"
    assert s["ratchet"]["state"] == "invalid" and s["capabilities"]["ratchet"]["state"] == "errored"
    ids = [r["ruleId"] for r in sarif["runs"][0]["results"]]
    assert "PL/ratchet-invalid" in ids and "PL/untagged-output" in ids
    untagged = next(r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/untagged-output")
    assert untagged["level"] == "error" and "ratchet" not in untagged["message"]["text"]
    assert "ratchet file: .plumb-line/ratchet.json (invalid)" in text


def test_ratchet_invalid_file_names_the_problem(tmp_path):
    root = _consumer(tmp_path, PY_OUT)
    (tmp_path / "repo" / ".plumb-line" / "ratchet.json").write_text('{"ratchet-format": "v9"}', encoding="utf-8")
    code, s, sarif, _ = _run(root, tmp_path, FakeRunner({"provenance_lint.py": (0, "[]", "")}))
    assert code == 1
    msg = next(r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/ratchet-invalid")["message"]["text"]
    assert "ratchet-format" in msg


def test_ratchet_tool_missing_output_capability_is_not_split(tmp_path):
    root = _consumer(tmp_path, PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::gone"]})
    fake = FakeRunner({}, missing=("python3",))
    code, s, _, text = _run(root, tmp_path, fake)
    assert code == 1 and s["ratchet"] == {"file": ".plumb-line/ratchet.json", "state": "ran", "known": 0,
                                          "new": 0, "stale": 0, "unmeasured": ["python.output"]}
    # Three zeros alone would read as "ratcheted and clean"; the head line
    # has to say the output capability was never measured.
    assert "1 unmeasured" in text.splitlines()[0]


def test_ratchet_sites_are_root_relative_but_sarif_is_workspace_relative(tmp_path):
    (tmp_path / "packages").mkdir()
    root = _consumer(tmp_path / "packages", PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::pinned"]})
    fake = FakeRunner({"provenance_lint.py": (0, "[]", ""),
                       "provenance_lint.py:output": (1, _untagged_issues(("src/p/b.py", "pinned")), "")})
    code, s, sarif, _ = _run(root, tmp_path, fake, workspace=str(tmp_path))
    assert code == 0 and s["ratchet"]["known"] == 1
    result = next(r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/untagged-output")
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "packages/repo/src/p/b.py"


def test_no_ratchet_key_means_no_ratchet_block(tmp_path):
    root = _consumer(tmp_path, {k: v for k, v in PY_OUT.items() if k != "ratchet"})
    code, s, _, text = _run(root, tmp_path, FakeRunner({"provenance_lint.py": (0, "[]", "")}))
    # Not a bare "ratchet" not in text: the pytest tmp_path for this test's
    # own name embeds "ratchet" in the SARIF path the summary always
    # prints. Assert the absence of the ratchet clause/block specifically.
    assert code == 0 and s["ratchet"] is None and "ratchet:" not in text and "ratchet file:" not in text
    assert "| ratchet |" not in text


# ---------- final review A: an empty ESLint file list is no match, not clean ----------

JS_OUT = {"enforcement-format": "v1", "languages": ["js"],
          "js": {"provenance": {"config": "eslint-provenance.cjs",
                                "globs": ["src/**/*.js"], "outputGlobs": ["src/p/**/*.js"]}},
          "ratchet": {"file": ".plumb-line/ratchet.json"}}


def test_js_output_empty_eslint_array_is_no_match_not_clean(tmp_path):
    # ESLint --format json emits one entry per LINTED file even when that file
    # has zero messages, so a top-level `[]` means no file was linted at all —
    # a broken outputGlobs. Read as "clean", the ratchet would conclude every
    # pinned JS site was fixed: `prune` would erase them and `update` pin [].
    root = _consumer(tmp_path, JS_OUT)
    _ratchet(root, {"js.output": ["src/p/b.js::f"]})
    code, s, sarif, _ = _run(root, tmp_path, FakeRunner({"eslint": (0, "[]", "")}))
    cap = s["capabilities"]["js.output"]
    assert cap["state"] == "ran" and cap["note"] == R.NO_MATCH_NOTE
    assert s["ratchet"]["stale"] == 0 and s["ratchet"]["unmeasured"] == ["js.output"]
    assert not [r for r in sarif["runs"][0]["results"] if r["ruleId"] == "PL/ratchet-stale"]
    assert code == 1, "#395: a ratchet is configured, so an unmeasured surface fails the job"


def test_js_output_one_clean_linted_file_is_a_real_ran_with_no_note(tmp_path):
    # The other side of the same coin: ESLint DID lint a file and found
    # nothing. That is a measured, clean run — state `ran`, no note.
    root = _consumer(tmp_path, {k: v for k, v in JS_OUT.items() if k != "ratchet"})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"), "messages": []}])
    code, s, _, _ = _run(root, tmp_path, FakeRunner({"eslint": (0, payload, "")}))
    cap = s["capabilities"]["js.output"]
    assert code == 0 and (cap["state"], cap["parser"], cap["note"]) == ("ran", "json", None)
    assert cap["results"] == 0


# ---------- #395: a configured ratchet cannot pass over a surface nothing measured ----------

NO_MATCH_OUT = {"enforcement-format": "v1", "languages": ["python"],
                "python": {"provenance": {"globs": ["src/**/*.py"], "outputGlobs": ["nothing/**/*.py"]}},
                "ratchet": {"file": ".plumb-line/ratchet.json"}}


def test_ratcheted_surface_that_was_never_measured_fails_regardless_of_fail_on(tmp_path):
    # A typo'd or stale outputGlobs used to leave a ratcheted job green: the
    # only signals were `N unmeasured` in the head line and the summary JSON.
    # "The ratchet is configured and its surface was never measured" is a
    # fail-regardless condition, the same class as a missing tool.
    root = _consumer(tmp_path, NO_MATCH_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::pinned"]})
    fake = FakeRunner({"provenance_lint.py": (0, "[]", "")})
    code, s, _, text = _run(root, tmp_path, fake, fail_on="none")
    assert code == 1
    assert s["findings"] == 0 and s["ratchet"]["unmeasured"] == ["python.output"]
    # The message names the capability and the globs that measured nothing.
    assert "python.output" in text and "nothing/**/*.py" in text and R.NO_MATCH_NOTE in text


def test_unmeasured_surface_without_a_configured_ratchet_is_still_green(tmp_path):
    # Unchanged where no ratchet is configured: a no-match capability is
    # `ran` with zero results and proves nothing, but nothing was pinned on
    # it, so there is no claim to contradict.
    root = _consumer(tmp_path, {k: v for k, v in NO_MATCH_OUT.items() if k != "ratchet"})
    code, s, _, _ = _run(root, tmp_path, FakeRunner({"provenance_lint.py": (0, "[]", "")}))
    assert code == 0 and s["ratchet"] is None
    assert s["capabilities"]["python.output"]["note"] == R.NO_MATCH_NOTE


def test_unparsed_surface_file_leaves_the_output_capability_unmeasured(tmp_path):
    # #392: a surface file provenance_lint.py could not parse (rule `parse`,
    # a syntax error) is one require-provenance-output never ran on. The
    # capability used to stay a plain `ran`, so the ratchet measured the
    # surface as if that file had no sites — `update` would pin the set,
    # `prune` would drop whatever the unreadable file used to hold.
    root = _consumer(tmp_path, PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::pinned"]})
    syntax = json.dumps([{"filename": "src/p/b.py", "line": 1, "rule": "parse",
                          "message": "syntax error: invalid syntax"}])
    fake = FakeRunner({"provenance_lint.py": (0, "[]", ""), "provenance_lint.py:output": (1, syntax, "")})
    code, s, sarif, text = _run(root, tmp_path, fake, fail_on="none")
    cap = s["capabilities"]["python.output"]
    assert cap["state"] == "ran" and cap["note"] == RT.UNPARSED_PREFIX + "src/p/b.py"
    assert s["ratchet"]["unmeasured"] == ["python.output"]
    # Unmeasured, so nothing is split and nothing is pruned: the pinned site
    # is neither a known-note nor a stale-note, and the job fails outright.
    assert s["ratchet"]["known"] == 0 and s["ratchet"]["stale"] == 0
    assert [r["ruleId"] for r in sarif["runs"][0]["results"]] == ["PL/unparsed"]
    assert code == 1 and "src/p/b.py" in text


def test_js_unparsed_surface_file_leaves_js_output_unmeasured(tmp_path):
    # The JS half of the same rule: an ESLint fatal (ruleId null) on a file
    # inside outputGlobs. Same for a require-provenance-output message with
    # no [site: …] marker — a site the assembler could not key.
    root = _consumer(tmp_path, JS_OUT)
    _ratchet(root, {"js.output": ["src/p/b.js::f"]})
    fatal = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"),
                         "messages": [{"ruleId": None, "fatal": True, "severity": 2,
                                      "message": "Parsing error: Unexpected token", "line": 1, "column": 8}]}])
    fake = FakeRunner({"eslint:src/p/**/*.js": (1, fatal, ""), "eslint": (0, "[]", "")})
    code, s, _, _ = _run(root, tmp_path, fake, fail_on="none")
    assert code == 1 and s["capabilities"]["js.output"]["note"] == RT.UNPARSED_PREFIX + "src/p/b.js"
    assert s["ratchet"]["unmeasured"] == ["js.output"]


def test_unparsed_file_outside_an_output_surface_leaves_the_capability_measured(tmp_path):
    # The rule is scoped to the output capabilities: an item the assembler
    # could not map in js.provenance's or python.provenance's run says
    # nothing about whether the OUTPUT surface was measured.
    root = _consumer(tmp_path, PY_OUT)
    _ratchet(root, {"python.output": ["src/p/b.py::pinned"]})
    syntax = json.dumps([{"filename": "src/a.py", "line": 1, "rule": "parse", "message": "syntax error: bad"}])
    fake = FakeRunner({"provenance_lint.py": (1, syntax, ""),
                       "provenance_lint.py:output": (1, _untagged_issues(("src/p/b.py", "pinned")), "")})
    code, s, _, _ = _run(root, tmp_path, fake, fail_on="none")
    assert s["capabilities"]["python.provenance"]["note"] is None
    assert s["ratchet"] == {"file": ".plumb-line/ratchet.json", "state": "ran", "known": 1, "new": 0,
                            "stale": 0, "unmeasured": []}
    assert code == 0


def test_js_boundary_no_match_note_says_what_it_lints_not_globs(tmp_path):
    # js.boundary lints `.`, never a glob list, so the output surface's
    # no-match note would misdescribe what did not happen.
    root = _consumer(tmp_path, _JS_ONLY)
    code, s, _, _ = _run(root, tmp_path, FakeRunner({"eslint:.": (0, "[]", "")}))
    note = s["capabilities"]["js.boundary"]["note"]
    assert code == 0 and s["capabilities"]["js.boundary"]["state"] == "ran"
    assert note == R.NO_LINTED_FILES_NOTE and note != R.NO_MATCH_NOTE and "glob" not in note
