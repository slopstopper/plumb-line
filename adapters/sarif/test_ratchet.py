"""Tests for adapters/sarif/ratchet.py — the provenance ratchet (#119).

Run from the repo root:  python3 -m pytest -q adapters/sarif
"""
import json
import os

from adapters.sarif import assemble as A
from adapters.sarif import ratchet as RT


def _ok():
    return {"ratchet-format": "v1",
            "sites": {"js.output": ["src/fx.mjs::applyFx"], "python.output": []},
            "history": [{"date": "2026-09-15", "because": "initial pin", "change": "pinned 1 site"}]}


def _untagged(cap, file, site, **kw):
    r = A.result("PL/untagged-output", "Untagged output", file=file, line=3, tool="x", site=site, **kw)
    r["capability"] = cap
    return r


# ---------- contract ----------

def test_valid_file_has_no_problems():
    assert RT.validate_ratchet(_ok()) == []


def test_empty_is_valid_and_canonical():
    e = RT.empty()
    assert RT.validate_ratchet(e) == [] and list(e) == RT.KEYS
    assert RT.dumps(e) == json.dumps(e, indent=2, sort_keys=True) + "\n"


def test_unknown_format_and_keys_are_problems():
    d = dict(_ok(), **{"ratchet-format": "v9", "extra": 1})
    p = RT.validate_ratchet(d)
    assert any("ratchet-format" in x for x in p) and any("unknown key: extra" in x for x in p)


def test_sites_must_be_output_capabilities_with_sorted_unique_site_lists():
    d = _ok()
    d["sites"]["baselines"] = []
    d["sites"]["js.output"] = ["b::f", "a::g", "a::g"]
    p = RT.validate_ratchet(d)
    assert any("sites.baselines" in x for x in p)
    assert any("sorted" in x or "unique" in x for x in p)


def test_malformed_sites_are_problems():
    for bad in ("nosep", "/abs/path::f", "../up.py::f", "a.py::", "::f", 7):
        d = _ok()
        d["sites"]["js.output"] = [bad]
        assert RT.validate_ratchet(d), bad


def test_history_entries_need_date_because_change():
    d = _ok()
    d["history"] = [{"date": "2026-9-1", "because": "", "change": "x"}]
    p = RT.validate_ratchet(d)
    assert any("date" in x for x in p) and any("because" in x for x in p)
    d["history"] = "nope"
    assert RT.validate_ratchet(d)


def test_not_an_object_is_one_problem():
    assert RT.validate_ratchet([]) == ["ratchet file is not a JSON object"]


def test_load_missing_and_unparsable(tmp_path):
    data, p = RT.load_ratchet(str(tmp_path / "r.json"))
    assert data is None and p == [f"ratchet file not found: {tmp_path / 'r.json'}"]
    (tmp_path / "r.json").write_text("{", encoding="utf-8")
    data, p = RT.load_ratchet(str(tmp_path / "r.json"))
    assert data is None and p and "cannot parse" in p[0]


def test_write_is_canonical_and_stable(tmp_path):
    path = str(tmp_path / "d" / "r.json")
    RT.write_ratchet(path, _ok())
    first = open(path, encoding="utf-8").read()
    data, p = RT.load_ratchet(path)
    assert p == [] and data == _ok()
    RT.write_ratchet(path, data)
    assert open(path, encoding="utf-8").read() == first
    assert first.endswith("\n") and '"ratchet-format": "v1"' in first
    assert not [f for f in os.listdir(os.path.dirname(path)) if f != "r.json"], "no tmp file left behind"


def test_write_unlinks_the_tmp_file_when_the_write_raises(tmp_path, monkeypatch):
    path = str(tmp_path / "r.json")
    original = "not touched"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(original)

    def _boom(data):
        raise RuntimeError("disk full")

    monkeypatch.setattr(RT, "dumps", _boom)
    try:
        RT.write_ratchet(path, _ok())
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass
    assert not [f for f in os.listdir(str(tmp_path)) if f.startswith("r.json.tmp-")], \
        "no tmp file left behind after a failed write"
    assert open(path, encoding="utf-8").read() == original, "existing target left untouched"


def test_write_reraises_the_original_error_even_when_the_tmp_cleanup_also_fails(tmp_path, monkeypatch):
    # The cleanup unlink is best-effort: if it raises too (e.g. the tmp file
    # is gone, or another permission problem), the ORIGINAL write/replace
    # error must still be what propagates, not the cleanup's OSError.
    path = str(tmp_path / "r.json")

    def _boom(data):
        raise RuntimeError("disk full")

    monkeypatch.setattr(RT, "dumps", _boom)
    monkeypatch.setattr(RT.os, "unlink", lambda p: (_ for _ in ()).throw(OSError("cleanup also failed")))
    try:
        RT.write_ratchet(path, _ok())
        assert False, "expected RuntimeError to propagate"
    except RuntimeError as e:
        assert "disk full" in str(e), "the original error, not the cleanup's OSError"


# ---------- apply ----------

RAN = ("ran", "json", None)


def test_known_site_becomes_a_note_and_new_stays_an_error():
    results = [_untagged("js.output", "src/fx.mjs", "applyFx"), _untagged("js.output", "src/fx.mjs", "total")]
    out, s = RT.apply(results, {"js.output": RAN, "python.output": RAN}, _ok())
    assert s == {"known": 1, "new": 1, "stale": 0}
    known, new = out[0], out[1]
    assert known["level"] == "note" and known["message"].startswith(RT.KNOWN_PREFIX)
    assert new["level"] == "error" and new["message"].endswith(RT.NEW_SUFFIX)
    assert results[0]["level"] == "error", "apply never mutates its input"


def test_stale_site_is_one_note_naming_the_site():
    out, s = RT.apply([], {"js.output": RAN, "python.output": RAN}, _ok())
    assert s == {"known": 0, "new": 0, "stale": 1}
    assert out[0]["ruleId"] == "PL/ratchet-stale" and out[0]["level"] == "note"
    assert out[0]["message"] == RT.STALE_TEXT.format(site="src/fx.mjs::applyFx")
    assert out[0]["capability"] == "js.output" and out[0]["file"] == "src/fx.mjs"


def test_two_findings_in_one_function_are_one_site():
    results = [_untagged("js.output", "src/fx.mjs", "applyFx"),
               dict(_untagged("js.output", "src/fx.mjs", "applyFx"), line=9)]
    out, s = RT.apply(results, {"js.output": RAN}, _ok())
    assert s["known"] == 2 and s["stale"] == 0 and all(r["level"] == "note" for r in out)


def test_capability_that_did_not_run_is_not_split_and_yields_no_stale():
    r = _untagged("js.output", "src/fx.mjs", "applyFx")
    for state in (("tool-missing", None, "npm ci"), ("errored", "json", "exit 2"), ("ran", "json", RT.NO_MATCH_NOTE),
                  ("ran", "json", RT.UNPARSED_PREFIX + "src/fx.mjs")):
        out, s = RT.apply([r], {"js.output": state, "python.output": RAN}, _ok())
        assert s == {"known": 0, "new": 0, "stale": 0}, state
        assert out[0]["level"] == "error" and not out[0]["message"].endswith(RT.NEW_SUFFIX)


def test_sites_key_for_a_capability_the_manifest_dropped_is_one_stale_note():
    out, s = RT.apply([], {"python.output": RAN}, _ok())  # js.output absent from states
    assert s["stale"] == 1 and out[0]["ruleId"] == "PL/ratchet-stale"
    assert "js.output" in out[0]["message"] and out[0]["capability"] == "js.output"


def test_non_output_results_pass_through_untouched():
    r = A.result("PL/PB1", "PB1 m", file="a.py", tool="x")
    r["capability"] = "python.provenance"
    out, s = RT.apply([r], {"python.provenance": RAN, "python.output": RAN, "js.output": RAN}, RT.empty())
    assert out == [r] and s == {"known": 0, "new": 0, "stale": 0}


# ---------- CLI: update / prune ----------

from adapters.sarif.test_run_checks import FakeRunner, _consumer, _ROOT as _REPO  # noqa: E402

MAN = {"enforcement-format": "v1", "languages": ["python"],
       "python": {"provenance": {"globs": ["src/**/*.py"], "outputGlobs": ["src/p/**/*.py"]}},
       "ratchet": {"file": ".plumb-line/ratchet.json"}}


def _issues(*sites):
    return json.dumps([{"filename": f, "line": 2, "rule": "REQ-OUTPUT", "symbol": s, "message": "m"} for f, s in sites])


def _read(root):
    return json.load(open(os.path.join(root, ".plumb-line", "ratchet.json"), encoding="utf-8"))


def test_update_refuses_an_empty_because_and_writes_nothing(tmp_path):
    root = _consumer(tmp_path, MAN)
    for because in ("", "   ", None):
        code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, because,
                                 runner=FakeRunner({"provenance_lint.py": (0, "[]", "")}))
        assert code == 2 and msg == RT.BECAUSE_REQUIRED
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_update_creates_the_file_on_first_run_with_an_initial_pin(tmp_path):
    root = _consumer(tmp_path, MAN)
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "z"), ("src/p/b.py", "a"), ("src/p/b.py", "a")), "")})
    code, msg, data = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO,
                                "initial pin", runner=fake, today="2026-09-15")
    assert code == 0 and "pinned 2 sites" in msg
    on_disk = _read(root)
    assert on_disk == data and RT.validate_ratchet(on_disk) == []
    assert on_disk["sites"] == {"python.output": ["src/p/b.py::a", "src/p/b.py::z"]}
    assert on_disk["history"] == [{"date": "2026-09-15", "because": "initial pin",
                                   "change": "pinned 2 sites (python.output: 2)"}]


def test_update_records_growth_and_shrink_in_the_change_summary(tmp_path):
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    RT.update(root, m, _REPO, "initial pin", today="2026-09-15",
              runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a"), ("src/p/b.py", "b")), "")}))
    code, msg, data = RT.update(root, m, _REPO, "vendored module c", today="2026-09-16",
                                runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "b"), ("src/p/b.py", "c")), "")}))
    assert code == 0
    assert data["sites"]["python.output"] == ["src/p/b.py::b", "src/p/b.py::c"]
    assert data["history"][-1] == {"date": "2026-09-16", "because": "vendored module c",
                                   "change": "+1 -1 sites (python.output: +1 -1)"}
    assert len(data["history"]) == 2


def test_update_refuses_when_an_output_capability_could_not_be_measured(tmp_path):
    root = _consumer(tmp_path, MAN)
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({}, missing=("python3",)))
    assert code == 2 and "python.output" in msg and "tool-missing" in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_update_measured_but_empty_pins_an_empty_list_not_an_absent_key(tmp_path):
    root = _consumer(tmp_path, MAN)
    code, _, data = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "clean start",
                              runner=FakeRunner({"provenance_lint.py": (0, "[]", ""),
                                                  "provenance_lint.py:output": (0, "[]", "")}), today="2026-09-15")
    assert code == 0 and data["sites"] == {"python.output": []}


def test_update_drops_a_capability_the_manifest_no_longer_carries(tmp_path):
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    d = RT.empty()
    d["sites"] = {"js.output": ["src/x.mjs::f"], "python.output": ["src/p/b.py::a"]}
    d["history"] = [{"date": "2026-09-01", "because": "old", "change": "pinned 2 sites"}]
    RT.write_ratchet(os.path.join(root, ".plumb-line", "ratchet.json"), d)
    code, _, data = RT.update(root, m, _REPO, "js surface removed", today="2026-09-15",
                              runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")}))
    assert code == 0 and data["sites"] == {"python.output": ["src/p/b.py::a"]}
    assert data["history"][-1]["change"] == "+0 -1 sites (js.output: dropped 1; python.output: +0 -0)"


def test_prune_removes_only_stale_sites_and_needs_no_reason(tmp_path):
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    RT.update(root, m, _REPO, "initial pin", today="2026-09-15",
              runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a"), ("src/p/b.py", "b")), "")}))
    # b fixed, c is new: prune drops b and does NOT add c.
    code, msg, data = RT.prune(root, m, _REPO, today="2026-09-16",
                               runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a"), ("src/p/b.py", "c")), "")}))
    assert code == 0 and "pruned 1 stale site" in msg
    assert data["sites"] == {"python.output": ["src/p/b.py::a"]}
    assert data["history"][-1] == {"date": "2026-09-16", "because": "prune", "change": "-1 sites (python.output: -1)"}


def test_prune_is_a_byte_identical_noop_when_nothing_is_stale(tmp_path):
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")})
    RT.update(root, m, _REPO, "initial pin", runner=fake, today="2026-09-15")
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    before = open(path, encoding="utf-8").read()
    code, msg, _ = RT.prune(root, m, _REPO, runner=fake)
    assert code == 0 and msg == "nothing to prune" and open(path, encoding="utf-8").read() == before


def test_prune_without_a_file_refuses(tmp_path):
    root = _consumer(tmp_path, MAN)
    code, msg, _ = RT.prune(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO,
                            runner=FakeRunner({"provenance_lint.py": (0, "[]", "")}))
    assert code == 2 and "not found" in msg


def test_update_refuses_an_invalid_manifest(tmp_path):
    root = _consumer(tmp_path, dict(MAN, **{"enforcement-format": "v9"}))
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"provenance_lint.py:output": (0, "[]", "")}))
    assert code == 2 and "manifest invalid" in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_update_refuses_a_manifest_without_a_ratchet_key(tmp_path):
    no_ratchet = {k: v for k, v in MAN.items() if k != "ratchet"}
    root = _consumer(tmp_path, no_ratchet)
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"provenance_lint.py:output": (0, "[]", "")}))
    assert code == 2 and "names no ratchet file" in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_update_and_prune_refuse_an_invalid_existing_file_and_leave_it_untouched(tmp_path):
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"bogus": 1}))
    before = open(path, encoding="utf-8").read()
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")})
    code, msg, _ = RT.update(root, m, _REPO, "x", runner=fake)
    assert code == 2 and ("unknown key" in msg or "ratchet-format" in msg)
    assert open(path, encoding="utf-8").read() == before
    code, msg, _ = RT.prune(root, m, _REPO, runner=fake)
    assert code == 2 and ("unknown key" in msg or "ratchet-format" in msg)
    assert open(path, encoding="utf-8").read() == before


def test_update_without_a_manifest_points_at_bootstrap(tmp_path):
    root = str(tmp_path / "repo")
    os.makedirs(root, exist_ok=True)
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"provenance_lint.py:output": (0, "[]", "")}))
    assert code == 2 and "bootstrap" in msg


def test_main_update_and_prune_verbs(tmp_path, capsys, monkeypatch):
    root = _consumer(tmp_path, MAN)
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")})
    monkeypatch.setattr(RT, "_runner_for", lambda: fake)
    assert RT.main(["update", "--root", root, "--scripts-dir", _REPO, "--because", ""]) == 2
    assert RT.BECAUSE_REQUIRED in capsys.readouterr().out
    assert RT.main(["update", "--root", root, "--scripts-dir", _REPO, "--because", "initial pin", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sites"] == {"python.output": ["src/p/b.py::a"]}
    assert RT.main(["prune", "--root", root, "--scripts-dir", _REPO]) == 0
    assert "nothing to prune" in capsys.readouterr().out


# ---------- final review: JS no-match, idempotent update, blank `change` ----------

JS_MAN = {"enforcement-format": "v1", "languages": ["js"],
          "js": {"provenance": {"config": "eslint-provenance.cjs",
                                "globs": ["src/**/*.js"], "outputGlobs": ["src/p/**/*.js"]}},
          "ratchet": {"file": ".plumb-line/ratchet.json"}}


def _js_ratchet(root):
    d = RT.empty()
    d["sites"] = {"js.output": ["src/p/b.js::f"]}
    d["history"] = [{"date": "2026-09-15", "because": "initial pin", "change": "pinned 1 site"}]
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    RT.write_ratchet(path, d)
    return path


def test_update_refuses_when_js_output_matched_no_files(tmp_path):
    # An empty ESLint file list means nothing was linted. Pinning [] here
    # would silently erase the JS debt register on a typo'd outputGlobs.
    root = _consumer(tmp_path, JS_MAN)
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"eslint": (0, "[]", "")}))
    assert code == 2 and "js.output" in msg and RT.NO_MATCH_NOTE in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_prune_refuses_when_js_output_matched_no_files(tmp_path):
    root = _consumer(tmp_path, JS_MAN)
    path = _js_ratchet(root)
    before = open(path, "rb").read()
    code, msg, _ = RT.prune(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO,
                            runner=FakeRunner({"eslint": (0, "[]", "")}))
    assert code == 2 and "js.output" in msg and RT.NO_MATCH_NOTE in msg
    assert open(path, "rb").read() == before


def test_update_over_an_unchanged_tree_writes_nothing_and_says_so(tmp_path):
    # Idempotence: a second `update` on an unchanged tree must not append a
    # history entry (or a fresh date) for a change that did not happen.
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")})
    RT.update(root, m, _REPO, "initial pin", runner=fake, today="2026-09-15")
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    before = open(path, "rb").read()
    code, msg, data = RT.update(root, m, _REPO, "initial pin", runner=fake, today="2026-09-16")
    assert code == 0 and msg == "nothing changed"
    assert open(path, "rb").read() == before
    assert data["sites"] == {"python.output": ["src/p/b.py::a"]} and len(data["history"]) == 1


# ---------- #392: an unparsed file inside the output surface is not measurable ----------

def _syntax_error(filename):
    return json.dumps([{"filename": filename, "line": 1, "rule": "parse", "message": "syntax error: invalid syntax"}])


def test_measure_reports_an_unparsed_surface_file_as_unmeasured(tmp_path):
    # "Cannot pin what could not be measured" was enforced per TOOL; a file
    # inside the surface that the tool could not parse is one the output
    # check never ran on, so the capability measured nothing either.
    root = _consumer(tmp_path, MAN)
    manifest = json.load(open(os.path.join(root, ".plumb-line", "enforcement.json"), encoding="utf-8"))
    measured = RT.measure(root, manifest, _REPO,
                          runner=FakeRunner({"provenance_lint.py:output": (1, _syntax_error("src/p/b.py"), "")}))
    (state, sites) = measured["python.output"]
    assert state == ("ran", "json", RT.UNPARSED_PREFIX + "src/p/b.py")
    assert sites == [], "a surface that was not measured pins nothing"


def test_update_refuses_when_a_surface_file_could_not_be_parsed(tmp_path):
    root = _consumer(tmp_path, MAN)
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"provenance_lint.py:output": (1, _syntax_error("src/p/b.py"), "")}))
    assert code == 2 and "python.output" in msg and "src/p/b.py" in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_prune_refuses_when_a_surface_file_could_not_be_parsed(tmp_path):
    # The dangerous direction: pinned sites in the unreadable file look
    # "no longer reported", so prune would erase them.
    root = _consumer(tmp_path, MAN)
    m = os.path.join(root, ".plumb-line", "enforcement.json")
    RT.update(root, m, _REPO, "initial pin", today="2026-09-15",
              runner=FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")}))
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    before = open(path, "rb").read()
    code, msg, _ = RT.prune(root, m, _REPO,
                            runner=FakeRunner({"provenance_lint.py:output": (1, _syntax_error("src/p/b.py"), "")}))
    assert code == 2 and "python.output" in msg and "src/p/b.py" in msg
    assert open(path, "rb").read() == before


def test_update_refuses_when_an_eslint_surface_file_could_not_be_parsed(tmp_path):
    root = _consumer(tmp_path, JS_MAN)
    fatal = json.dumps([{"filePath": os.path.join(root, "src", "p", "b.js"),
                         "messages": [{"ruleId": None, "fatal": True, "severity": 2,
                                      "message": "Parsing error: Unexpected token", "line": 1, "column": 8}]}])
    code, msg, _ = RT.update(root, os.path.join(root, ".plumb-line", "enforcement.json"), _REPO, "x",
                             runner=FakeRunner({"eslint:src/p/**/*.js": (1, fatal, ""), "eslint": (0, "[]", "")}))
    assert code == 2 and "js.output" in msg and "src/p/b.js" in msg
    assert not os.path.exists(os.path.join(root, ".plumb-line", "ratchet.json"))


def test_history_change_must_not_be_blank():
    d = _ok()
    d["history"] = [{"date": "2026-09-15", "because": "why", "change": "  "}]
    assert any("change" in x for x in RT.validate_ratchet(d))


# ---------- #389: one measurability predicate, one public runner surface ----------

def _shape(tmp_path, name, manifest, runner, cap):
    """The raw (state, parser, note) the real runner hands `cap`, harvested
    through measure() rather than hand-written, so a runner that grows a new
    state shape shows up here instead of silently escaping the predicate."""
    root = _consumer(tmp_path / name, manifest)
    measured = RT.measure(root, manifest, _REPO, runner=runner)
    return measured[cap][0]


def test_measured_and_unmeasurable_agree_over_every_state_shape(tmp_path):
    # The shapes run_capabilities() can leave on an OUTPUT capability.
    # measured is the reader's predicate (apply) and _unmeasurable is the
    # writers' (update/prune); #389 made the second ask the first, and this
    # pins that they answer the same over every shape the runner produces.
    no_glob = json.loads(json.dumps(MAN))
    no_glob["python"]["provenance"]["outputGlobs"] = ["nowhere/**/*.py"]
    shapes = {
        "ran, no findings": _shape(tmp_path, "clean", MAN,
                                   FakeRunner({"provenance_lint.py:output": (0, "[]", "")}), "python.output"),
        "ran, sites found": _shape(tmp_path, "sites", MAN,
                                   FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")}),
                                   "python.output"),
        "ran, no files matched": _shape(tmp_path, "nomatch", no_glob,
                                        FakeRunner({"provenance_lint.py:output": (0, "[]", "")}), "python.output"),
        "ran, unparsed surface file (#392)": _shape(
            tmp_path, "unparsed", MAN,
            FakeRunner({"provenance_lint.py:output": (1, _syntax_error("src/p/b.py"), "")}), "python.output"),
        "tool-missing": _shape(tmp_path, "missing", MAN, FakeRunner({}, missing=("python3",)), "python.output"),
        "errored": _shape(tmp_path, "errored", MAN,
                          FakeRunner({"provenance_lint.py:output": (2, "", "boom")}), "python.output"),
        "ran, eslint linted nothing": _shape(tmp_path, "js", JS_MAN, FakeRunner({"eslint": (0, "[]", "")}),
                                             "js.output"),
    }
    # Each shape really is the one it is named for.
    assert shapes["ran, no findings"] == shapes["ran, sites found"] == ("ran", "json", None)
    assert shapes["ran, no files matched"][2] == RT.NO_MATCH_NOTE
    assert shapes["ran, eslint linted nothing"][2] == RT.NO_MATCH_NOTE
    assert shapes["ran, unparsed surface file (#392)"][2].startswith(RT.UNPARSED_PREFIX)
    assert shapes["tool-missing"][0] == "tool-missing" and shapes["errored"][0] == "errored"

    for why, st in shapes.items():
        cap = "js.output" if "eslint" in why else "python.output"
        measurable = RT.measured({cap: st}, cap)
        err = RT._unmeasurable({cap: (st, [])})
        assert measurable == (err is None), (why, st, err)
        if not measurable:
            assert cap in err and st[0] in err, (why, err)
    # An absent capability is unmeasured for the reader and invisible to the
    # writers (measure never yields a key the manifest does not carry).
    assert RT.measured({}, "python.output") is False
    assert RT._unmeasurable({}) is None


def test_ratchet_only_uses_the_public_run_checks_surface():
    # The dependency direction run_checks.py's docstring declares: ratchet
    # may import run_capabilities / resolver / default_runner lazily, and
    # nothing else. Scanned as SOURCE because the reach-in is what the
    # module-load cycle tempts, and no runtime assertion would catch it.
    import re
    src = open(RT.__file__, encoding="utf-8").read()
    reaches = re.findall(r"(?<![A-Za-z0-9_])(?:run_checks|R)\._[A-Za-z0-9_]*", src)
    assert reaches == [], f"ratchet.py reaches into run_checks privates: {reaches}"
    from adapters.sarif import run_checks as RC
    for name in ("run_capabilities", "resolver", "default_runner"):
        assert callable(getattr(RC, name)), name


def test_run_checks_only_uses_the_public_ratchet_surface():
    # The reverse direction is guarded too: run_checks imports ratchet at
    # module level as `RT`, so nothing stops it reaching into a ratchet
    # underscore name (e.g. RT._unmeasurable) instead of the public
    # `measured`. Scanned as SOURCE for the same reason as the sibling test.
    import re
    import adapters.sarif.run_checks as RC
    src = open(RC.__file__, encoding="utf-8").read()
    reaches = re.findall(r"(?<![A-Za-z0-9_])(?:ratchet|RT)\._[A-Za-z0-9_]*", src)
    assert reaches == [], f"run_checks.py reaches into ratchet privates: {reaches}"
