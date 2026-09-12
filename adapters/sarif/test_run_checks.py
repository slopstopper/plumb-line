"""Tests for adapters/sarif/run_checks.py — the Action's orchestrator (#118).

Run from the repo root:  python3 -m pytest -q adapters/sarif
The fake runner makes every tool's behaviour explicit; the last test runs the
real tools over the planted fixtures.
"""
import json
import os
import shutil

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
    """Answers each tool by whichever token in its command names the tool
    itself — a .py/.mjs script path, or a bare "eslint"/"lint-imports" —
    found anywhere in cmd, falling back to cmd[0] if none matches; records
    calls."""
    def __init__(self, answers, missing=()):
        self.answers, self.missing, self.calls = answers, set(missing), []

    def which(self, tool):
        return None if tool in self.missing else f"/usr/bin/{tool}"

    def __call__(self, cmd, cwd):
        self.calls.append((cmd, cwd))
        key = next((os.path.basename(a) for a in cmd if a.endswith((".py", ".mjs")) or a in ("eslint", "lint-imports")),
                   os.path.basename(cmd[0]))
        return self.answers.get(key, (0, "[]", ""))


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
    assert "pip install import-linter" in s["capabilities"]["python.boundary"]["note"]
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
    # Not the literal FULL constant: FULL also enables js.boundary, which
    # invokes eslint through the SAME FakeRunner key ("eslint" — the fake
    # can't distinguish boundary's config from provenance's), so it would
    # replay this same payload unfiltered and double every count below.
    # This keeps FULL's js.provenance/js.output shape and drops js.boundary
    # so "exactly one of each" is actually checking the capability filters,
    # not an artifact of the fake sharing one key across three invocations.
    root = _consumer(tmp_path, {"enforcement-format": "v1", "languages": ["js"],
                                "js": {"provenance": {"config": "eslint-provenance.cjs",
                                                      "globs": ["src/**/*.js"], "outputGlobs": ["src/p/**/*.js"]}}})
    payload = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"),
                           "messages": [{"ruleId": "plumb-line/no-provenance-bypass",
                                        "message": "PB1 laundered", "line": 1, "column": 1},
                                       {"ruleId": "plumb-line/require-provenance-output",
                                        "message": "untagged output", "line": 2, "column": 1}]}])
    fake = FakeRunner({"eslint": (0, payload, "")})
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


def test_end_to_end_over_the_planted_fixtures(tmp_path):
    """The only test that proves the mapping matches what the real tools emit.
    Skipped, loudly, if a tool is not installed locally — CI installs both."""
    import pytest
    missing = [t for t in ("node", "lint-imports") if shutil.which(t) is None]
    if missing:
        pytest.skip(f"real tools not installed locally: {missing}")
    for fixture, expect in (("examples/js-payments-service", {"PL/boundary"}),
                            ("examples/python-data-pipeline", {"PL/boundary"})):
        root = os.path.join(_ROOT, fixture, "broken")
        p = _paths(tmp_path / os.path.basename(fixture))
        os.makedirs(os.path.dirname(p["sarif_path"]), exist_ok=True)
        code = R.run(root, os.path.join(root, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                     version="t", **p)
        assert code == 1, fixture
        ids = {r["ruleId"] for r in json.load(open(p["sarif_path"]))["runs"][0]["results"]}
        assert expect <= ids, (fixture, ids)
        clean = os.path.join(_ROOT, fixture, "clean")
        code = R.run(clean, os.path.join(clean, ".plumb-line", "enforcement.json"), _ROOT, "findings",
                     version="t", **p)
        assert code == 0, (fixture, open(p["step_summary_path"]).read())
