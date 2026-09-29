"""Tests for scripts/breadth_routing.py — who won each breadth probe (#487).

Run from the repo root: python3 -m pytest -q scripts/test_breadth_routing.py
"""
import importlib.util
import json
import os

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breadth_routing.py")
_spec = importlib.util.spec_from_file_location("_breadth_routing", _SCRIPT)
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def _files(tmp_path, rows):
    queries = [{"query": q, "expected_skill": exp, "moment": "m", "principle": "p"}
               for q, exp, _ in rows]
    record = {"results": [{"query": q, "winners": winners} for q, _, winners in rows]}
    qp, rp = tmp_path / "q.json", tmp_path / "r.json"
    qp.write_text(json.dumps(queries), encoding="utf-8")
    rp.write_text(json.dumps(record), encoding="utf-8")
    return str(qp), str(rp)


def test_a_query_routes_when_its_skill_wins_at_least_half_the_probes(tmp_path):
    q, r = _files(tmp_path, [
        ("a", "plumb-line-method", ["plumb-line:plumb-line-method", None]),
        ("b", "plumb-line-adopt", ["plumb-line:plumb-line-method", None]),
        ("c", None, [None, None]),
        # a near-miss must win nothing on every probe
        ("d", None, [None, "plumb-line:plumb-line-audit"]),
    ])
    rows, by_skill = br.route(q, r)
    assert [row["routed"] for row in rows] == [True, False, True, False]
    assert by_skill == {"plumb-line-method": (1, 1), "plumb-line-adopt": (0, 1), "none": (1, 2)}


def test_the_winner_is_read_from_the_skill_field_without_its_plugin_prefix(tmp_path):
    q, r = _files(tmp_path, [("a", "plumb-line-audit", ["plumb-line:plumb-line-audit"])])
    rows, _ = br.route(q, r)
    assert rows[0]["winners"] == ["plumb-line-audit"]


def test_a_query_missing_from_the_record_is_an_error(tmp_path):
    import pytest
    q, _ = _files(tmp_path, [("a", None, [None])])
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"results": []}), encoding="utf-8")
    with pytest.raises(KeyError):
        br.route(q, str(other))


def test_derive_writes_the_eval_set_trigger_check_reads_for_one_target(tmp_path):
    # The committed breadth set carries expected_skill, not should_trigger;
    # derive() is the one reproducible step between them (#487 review).
    q, _ = _files(tmp_path, [("a", "plumb-line-method", []), ("b", None, []),
                             ("c", "plumb-line-adopt", [])])
    assert br.derive(q, "plumb-line-method") == [
        {"query": "a", "should_trigger": True},
        {"query": "b", "should_trigger": False},
        {"query": "c", "should_trigger": False}]


def test_a_query_with_no_probes_is_an_error_not_a_vacuous_route(tmp_path):
    import pytest
    q, r = _files(tmp_path, [("a", "plumb-line-method", [])])
    with pytest.raises(ValueError):
        br.route(q, r)


def test_derive_refuses_a_target_no_query_expects(tmp_path):
    # A typo would otherwise give an all-negative set that passes trivially.
    import pytest
    q, _ = _files(tmp_path, [("a", "plumb-line-method", [])])
    with pytest.raises(ValueError):
        br.derive(q, "plumb-line-methd")


def test_cli_usage_errors_exit_2_without_a_traceback(tmp_path, capsys):
    q, _ = _files(tmp_path, [("a", "plumb-line-method", [])])
    assert br.main(["--derive", "plumb-line-method"]) == 2
    assert br.main([q]) == 2
    assert br.main(["--derive", "plumb-line-methd", q]) == 2
    assert "no query expects" in capsys.readouterr().err
