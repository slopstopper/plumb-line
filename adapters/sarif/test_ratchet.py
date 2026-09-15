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
    for state in (("tool-missing", None, "npm ci"), ("errored", "json", "exit 2"), ("ran", "json", RT.NO_MATCH_NOTE)):
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
    assert code == 0 and "pruned 1" in msg
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


def test_main_update_and_prune_verbs(tmp_path, capsys, monkeypatch):
    root = _consumer(tmp_path, MAN)
    fake = FakeRunner({"provenance_lint.py:output": (1, _issues(("src/p/b.py", "a")), "")})
    monkeypatch.setattr(RT, "_runner_for", lambda root: fake)
    assert RT.main(["update", "--root", root, "--scripts-dir", _REPO, "--because", ""]) == 2
    assert RT.BECAUSE_REQUIRED in capsys.readouterr().out
    assert RT.main(["update", "--root", root, "--scripts-dir", _REPO, "--because", "initial pin", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sites"] == {"python.output": ["src/p/b.py::a"]}
    assert RT.main(["prune", "--root", root, "--scripts-dir", _REPO]) == 0
    assert "nothing to prune" in capsys.readouterr().out
