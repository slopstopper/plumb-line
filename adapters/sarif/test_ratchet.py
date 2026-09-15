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
