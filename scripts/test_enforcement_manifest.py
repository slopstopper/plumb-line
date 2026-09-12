"""Tests for scripts/check_enforcement_manifest.py — the enforcement manifest validator (#118).

Run from the repo root:  python3 -m pytest -q scripts/test_enforcement_manifest.py
"""
import importlib.util
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("_cem", os.path.join(_HERE, "check_enforcement_manifest.py"))
cem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cem)


def _root(tmp_path, files=("eslint-boundary.cjs", "eslint-provenance.cjs", ".importlinter")):
    for f in files:
        (tmp_path / f).write_text("// config\n", encoding="utf-8")
    (tmp_path / ".plumb-line" / "baselines").mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


def _manifest():
    return {
        "enforcement-format": "v1",
        "languages": ["js", "python"],
        "js": {"boundary": {"config": "eslint-boundary.cjs"},
               "provenance": {"config": "eslint-provenance.cjs", "globs": ["src/**/*.mjs"],
                              "outputGlobs": ["src/pricing/**/*.mjs"]}},
        "python": {"boundary": {"config": ".importlinter"},
                   "provenance": {"globs": ["src/**/*.py"], "outputGlobs": ["src/pricing/**/*.py"]}},
        "baselines": {"dir": ".plumb-line/baselines"},
    }


def test_valid_manifest_has_no_issues(tmp_path):
    assert cem.validate_manifest(_manifest(), _root(tmp_path)) == []


def test_unknown_format_is_an_issue(tmp_path):
    m = _manifest()
    m["enforcement-format"] = "v9"
    assert any("enforcement-format" in i and "v9" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_missing_referenced_config_is_an_issue(tmp_path):
    m = _manifest()
    issues = cem.validate_manifest(m, _root(tmp_path, files=("eslint-provenance.cjs", ".importlinter")))
    assert any("eslint-boundary.cjs" in i and "not found" in i for i in issues), issues


def test_empty_or_non_string_globs_are_issues(tmp_path):
    m = _manifest()
    m["js"]["provenance"]["globs"] = []
    assert any("js.provenance.globs" in i for i in cem.validate_manifest(m, _root(tmp_path)))
    m = _manifest()
    m["python"]["provenance"]["outputGlobs"] = ["ok", ""]
    assert any("python.provenance.outputGlobs" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_languages_must_match_sections(tmp_path):
    m = _manifest()
    m["languages"] = ["js"]
    assert any("languages" in i and "python" in i for i in cem.validate_manifest(m, _root(tmp_path)))
    m = _manifest()
    del m["python"]
    m["languages"] = ["js", "python"]
    assert any("languages" in i and "python" in i for i in cem.validate_manifest(m, _root(tmp_path)))
    m = _manifest()
    m["languages"] = []
    assert any("languages" in i and "non-empty" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_unknown_keys_at_any_level_are_issues(tmp_path):
    m = _manifest()
    m["extra"] = 1
    assert any("unknown key" in i and "extra" in i for i in cem.validate_manifest(m, _root(tmp_path)))
    m = _manifest()
    m["js"]["boundary"]["zones"] = []
    assert any("unknown key" in i and "js.boundary.zones" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_baselines_dir_must_exist_when_present(tmp_path):
    m = _manifest()
    m["baselines"]["dir"] = "nowhere"
    assert any("baselines.dir" in i and "not found" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_not_an_object_is_one_issue():
    assert cem.validate_manifest(None, ".") == ["manifest is not a JSON object"]
    assert cem.validate_manifest([], ".") == ["manifest is not a JSON object"]


def test_capabilities_reflect_what_is_present():
    caps = cem.capabilities(_manifest())
    assert set(caps) == set(cem.CAPABILITY_KEYS)
    m = _manifest()
    del m["js"]["provenance"]["outputGlobs"]
    del m["baselines"]
    caps = cem.capabilities(m)
    assert "js.output" not in caps and "baselines" not in caps and "js.provenance" in caps


def test_load_manifest_distinguishes_missing_invalid_and_valid(tmp_path):
    root = _root(tmp_path)
    m, issues = cem.load_manifest(os.path.join(root, "nope.json"), root)
    assert m is None and issues == ["manifest not found: " + os.path.join(root, "nope.json")]
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    m, issues = cem.load_manifest(str(p), root)
    assert m is None and issues and issues[0].startswith("cannot parse")
    p = tmp_path / "good.json"
    p.write_text(json.dumps(_manifest()), encoding="utf-8")
    m, issues = cem.load_manifest(str(p), root)
    assert m == _manifest() and issues == []


def test_cli_exit_codes(tmp_path, capsys):
    root = _root(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_manifest()), encoding="utf-8")
    assert cem.main([str(p), "--root", root]) == 0
    assert "7 capabilit" in capsys.readouterr().out
    bad = _manifest()
    bad["enforcement-format"] = "v9"
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert cem.main([str(p), "--root", root]) == 1


def test_provenance_globs_is_required(tmp_path):
    m = _manifest()
    del m["python"]["provenance"]["globs"]
    assert any("python.provenance.globs is required" in i for i in cem.validate_manifest(m, _root(tmp_path)))


def test_js_provenance_config_required_and_must_exist(tmp_path):
    root = _root(tmp_path)
    m = _manifest()
    del m["js"]["provenance"]["config"]
    issues = cem.validate_manifest(m, root)
    assert any("js.provenance.config must be a non-empty string" in i for i in issues)
    m = _manifest()
    m["js"]["provenance"]["config"] = "does-not-exist.cjs"
    issues = cem.validate_manifest(m, root)
    assert any("js.provenance.config not found" in i for i in issues)


def test_values_beginning_with_a_dash_are_issues(tmp_path):
    # Globs are passed to ESLint positionally, so "--fix" would become a flag;
    # configs and dirs likewise. Reject at the manifest, not at the command.
    root = _root(tmp_path)
    for path, key in ((("js", "provenance", "globs"), "js.provenance.globs"),
                      (("python", "provenance", "outputGlobs"), "python.provenance.outputGlobs")):
        m = _manifest()
        m[path[0]][path[1]][path[2]] = ["src/**/*.x", "--fix"]
        assert f"{key}: values must not begin with '-'" in cem.validate_manifest(m, root)
    for path, key in ((("js", "boundary", "config"), "js.boundary.config"),
                      (("js", "provenance", "config"), "js.provenance.config"),
                      (("baselines", "dir"), "baselines.dir")):
        m = _manifest()
        node = m
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = "-" + node[path[-1]]
        assert f"{key}: values must not begin with '-'" in cem.validate_manifest(m, root), key
    assert cem.validate_manifest(_manifest(), root) == []


def test_paths_must_stay_inside_the_repository(tmp_path):
    root = _root(tmp_path)
    m = _manifest()
    m["js"]["boundary"]["config"] = "/etc/hostname"
    issues = cem.validate_manifest(m, root)
    assert any("js.boundary.config must be a relative path inside the repository" in i for i in issues)
    m = _manifest()
    m["baselines"]["dir"] = "../outside"
    issues = cem.validate_manifest(m, root)
    assert any("baselines.dir must be a relative path inside the repository" in i for i in issues)
