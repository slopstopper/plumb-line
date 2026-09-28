"""Tests for scripts/trigger_check.py — the tiered skill-trigger harness (#291).

Covers the pure logic only (matching, scoring, tier selection/merge); the
claude -p probing is exercised manually, not in CI.

Run from the repo root:

    python3 -m pytest -q scripts/test_trigger_check.py
"""
import importlib.util
import os

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "trigger_check.py")
_spec = importlib.util.spec_from_file_location("_trigger_check", _SCRIPT)
tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tc)


def test_skill_match_on_field_not_substring():
    # The 2026-08-18 artifact: a query naming plumb-line-audit.md put the
    # string into remediate's args; a raw substring match counted it as an
    # audit trigger. Matching must read the "skill" field.
    remediate = '{"skill": "plumb-line:plumb-line-remediate", "args": "apply plumb-line-audit.md"}'
    audit = '{"skill": "plumb-line:plumb-line-audit"}'
    bare = '{"skill": "plumb-line-audit"}'
    assert tc.skill_match(remediate, "plumb-line-audit") is False
    assert tc.skill_match(audit, "plumb-line-audit") is True
    assert tc.skill_match(bare, "plumb-line-audit") is True
    assert tc.skill_match("not json {", "plumb-line-audit") is False


def test_skill_name_extraction_for_miss_diagnostics():
    # On a miss the harness records WHICH skill won, distinguishing
    # "another skill captured it" from "answered inline with no skill".
    assert tc.skill_name('{"skill": "plumb-line:plumb-line-method"}') == "plumb-line:plumb-line-method"
    assert tc.skill_name("not json {") is None
    assert tc.skill_name('{"args": "no skill field"}') is None


def test_score_pass_rules():
    rows = [
        {"should_trigger": True, "runs": [True, True]},
        {"should_trigger": True, "runs": [False, False]},
        {"should_trigger": False, "runs": [False]},
        {"should_trigger": False, "runs": [True]},
    ]
    scored = tc.score(rows)
    assert [r["pass"] for r in scored] == [True, False, True, False]
    assert scored[0]["trigger_rate"] == 1.0


def test_contested_selection_only_reruns_screen_failures():
    scored = [
        {"query": "a", "should_trigger": True, "pass": True},
        {"query": "b", "should_trigger": True, "pass": False},
        {"query": "c", "should_trigger": False, "pass": False},
        {"query": "d", "should_trigger": False, "pass": True},
    ]
    contested = tc.contested(scored)
    assert [r["query"] for r in contested] == ["b", "c"]


def test_installed_locations_finds_target_and_reports_absence(tmp_path):
    # The 2026-08-18 void run: the target skill did not exist in the probe
    # environment (installed plugin predated it), and 0/10 read as a
    # description gap. The preflight must find where the target is actually
    # installed — and say "nowhere" loudly.
    root = tmp_path / "cache"
    (root / "slopstopper" / "plumb-line" / "0.7.3" / "skills" / "plumb-line-audit").mkdir(parents=True)
    (root / "other" / "toolkit" / "1.0.0" / "skills" / "unrelated").mkdir(parents=True)
    hits = tc.installed_locations("plumb-line-audit", str(root))
    assert hits == [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"}]
    assert tc.installed_locations("plumb-line-adopt", str(root)) == []


def test_stale_installs_flags_versions_behind_the_repo():
    # #295: plugin updates are manual and easy to miss — the owner's install
    # sat at 0.7.3 with 0.9.0 released, voiding a whole measurement run. The
    # preflight compares probed installs against this repo's own version and
    # warns; measuring a stale install stays allowed, but never silently.
    installs = [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"},
                {"plugin": "slopstopper/plumb-line", "version": "0.9.0"},
                {"plugin": "other/thing", "version": "2.0.0"}]
    stale = tc.stale_installs(installs, "0.9.0")
    assert stale == [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"}]
    # Non-semver versions are never flagged (unknown, not stale).
    assert tc.stale_installs([{"plugin": "x", "version": "dev"}], "0.9.0") == []


def test_merge_labels_rates_by_model_tier():
    screen = [
        {"query": "a", "should_trigger": True, "pass": True, "trigger_rate": 1.0},
        {"query": "b", "should_trigger": True, "pass": False, "trigger_rate": 0.0},
    ]
    confirm = [
        {"query": "b", "should_trigger": True, "pass": True, "trigger_rate": 1.0},
    ]
    merged = tc.merge(screen, confirm, screen_model="m-small", confirm_model="m-big")
    by_q = {r["query"]: r for r in merged}
    # Uncontested keeps the screen verdict, labeled with the screen model.
    assert by_q["a"]["measured_by"] == "m-small"
    # Contested takes the confirm verdict, labeled with the confirm model,
    # and keeps the screen result visible rather than overwriting history.
    assert by_q["b"]["measured_by"] == "m-big"
    assert by_q["b"]["pass"] is True
    assert by_q["b"]["screen"] == {"trigger_rate": 0.0, "pass": False}


# --- #317: the results JSON is a contracted measurement record --------------

def _merged():
    return [
        {"query": "a", "should_trigger": True, "runs": [True, True],
         "winners": ["plumb-line-audit", "plumb-line-audit"],
         "trigger_rate": 1.0, "pass": True, "measured_by": "haiku"},
        {"query": "b", "should_trigger": False, "runs": [True],
         "winners": ["other"], "trigger_rate": 1.0, "pass": False,
         "measured_by": "haiku"},
    ]


_ENV = {"plugins": ["agents-md@builtin", "plumb-line@inline"], "mcp_servers": []}


def _payload(**over):
    base = dict(target="t", installs=[], tiers={"screen": "haiku", "confirm": None},
                runs={"screen": 1, "confirm": 2}, threshold=0.5, timeout=150,
                merged=_merged(), isolation_flags=[],
                environments=tc.summarise_environments([_ENV, _ENV, _ENV]))
    base.update(over)
    return tc.build_payload(**base)


def test_score_honours_an_injected_threshold():
    rows = [{"should_trigger": True, "runs": [True, False]}]      # rate 0.5
    assert tc.score(rows, threshold=0.5)[0]["pass"] is True
    assert tc.score(rows, threshold=0.75)[0]["pass"] is False


def test_payload_carries_its_contract_and_its_conditions():
    payload = _payload(target="plumb-line-audit",
                       installs=[{"plugin": "o/p", "version": "0.10.0"}])
    keys = list(payload)
    assert keys[0] == "results-format" and payload["results-format"] == tc.RESULTS_FORMAT
    assert payload["threshold"] == 0.5
    assert payload["runs"] == {"screen": 1, "confirm": 2}
    assert payload["summary"] == {"passed": 1, "total": 2}
    assert payload["results"] == _merged()


def test_payload_records_the_probe_settings_that_change_verdicts():
    # #400: a timed-out run records as a non-trigger, and the turn cap bounds
    # whether a Skill call can happen at all — both must be on the record.
    payload = _payload(timeout=90)
    assert payload["results-format"] == "v3"
    assert payload["probe"] == {"timeout_s": 90, "max_turns": tc.MAX_TURNS,
                                "isolation_flags": []}


def test_probe_command_uses_the_recorded_turn_cap():
    cmd = tc.probe_cmd("q", "some-model")
    assert cmd[cmd.index("--max-turns") + 1] == str(tc.MAX_TURNS)


def test_validate_refuses_a_record_without_probe_settings():
    payload = _payload()
    del payload["probe"]
    assert any("probe" in i for i in tc.validate_results(payload))


def test_validate_refuses_a_v1_record_as_unreproducible():
    payload = _payload()
    del payload["probe"]
    payload["results-format"] = "v1"
    issues = tc.validate_results(payload)
    assert any("v1" in i and "timeout" in i for i in issues), issues


def test_validate_flags_malformed_probe_settings():
    for bad in ({"timeout_s": 0, "max_turns": 2}, {"timeout_s": 150, "max_turns": True},
                {"timeout_s": "150", "max_turns": 2}, {"timeout_s": 150}, [150, 2]):
        payload = _payload()
        payload["probe"] = bad
        assert any("probe" in i for i in tc.validate_results(payload)), bad


def test_validate_accepts_the_harness_own_payload():
    assert tc.validate_results(_payload()) == []


def test_validate_flags_missing_contract_and_unknown_version():
    payload = _payload()
    del payload["results-format"]
    assert any("results-format" in i for i in tc.validate_results(payload))
    payload["results-format"] = "v9"
    assert any("v9" in i for i in tc.validate_results(payload))


def test_validate_flags_a_verdict_inconsistent_with_the_stamped_threshold():
    # A stored pass must be reproducible from rate, threshold and expectation;
    # a row that says pass while its numbers say fail is a laundered verdict.
    payload = _payload()
    payload["results"][1]["pass"] = True
    issues = tc.validate_results(payload)
    assert any("row 2" in i and "pass" in i for i in issues), issues


def test_validate_flags_a_threshold_outside_the_unit_interval():
    payload = _payload()
    payload["threshold"] = 1.5
    assert any("threshold" in i for i in tc.validate_results(payload))


def test_validate_rejects_a_boolean_threshold():
    payload = _payload()
    payload["threshold"] = True
    assert any("threshold" in i for i in tc.validate_results(payload))


def test_validate_flags_a_summary_that_does_not_add_up():
    payload = _payload()
    payload["summary"]["passed"] = 2
    assert any("summary" in i for i in tc.validate_results(payload))


def test_cli_threshold_flag_and_its_default():
    args = tc.parse_args(["evals.json", "t", "out.json"])
    assert args.threshold == tc.THRESHOLD == 0.5
    args = tc.parse_args(["evals.json", "t", "out.json", "--threshold", "0.75"])
    assert args.threshold == 0.75


def test_cli_validate_mode_reads_a_results_file(tmp_path):
    import json
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_payload()), encoding="utf-8")
    assert tc.main(["--validate", str(good)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text('{"target": "t"}', encoding="utf-8")
    assert tc.main(["--validate", str(bad)]) == 1


def test_cli_timeout_must_be_positive():
    # The writer must not produce a record its own validator refuses.
    import pytest
    for bad in ("0", "-5"):
        with pytest.raises(SystemExit):
            tc.parse_args(["evals.json", "t", "out.json", "--timeout", bad])


def test_v1_refusal_names_what_is_missing_without_promising_reproduction():
    payload = _payload()
    del payload["probe"]
    payload["results-format"] = "v1"
    msg = next(i for i in tc.validate_results(payload) if "v1" in i)
    assert "cannot be reproduced" not in msg and "timeout" in msg


# ---------- #487: probing a checkout in isolation ----------

def test_probe_command_isolates_a_plugin_dir():
    # --plugin-dir alone would load the checkout beside the installed copy
    # (same plugin name), the user's other plugins' SessionStart hooks (9 on
    # the owner's machine, 2026-09-28) and 3 claude.ai connectors: every rate
    # would describe that environment, not the description.
    cmd = tc.probe_cmd("q", "m", plugin_dir="/co")
    assert cmd[cmd.index("--plugin-dir") + 1] == "/co"
    assert cmd[-len(tc.ISOLATION_FLAGS):] == tc.ISOLATION_FLAGS
    assert tc.ISOLATION_FLAGS == ["--setting-sources", "project", "--strict-mcp-config"]
    plain = tc.probe_cmd("q", "m")
    assert not set(tc.ISOLATION_FLAGS + ["--plugin-dir"]) & set(plain)


def _checkout(tmp_path, description="Use when x."):
    import json
    (tmp_path / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "plumb-line", "version": "0.11.5"}), encoding="utf-8")
    skill = tmp_path / "skills" / "plumb-line-method"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: plumb-line-method\ndescription: {description}\n---\n\n# body\n",
        encoding="utf-8")
    return tmp_path


def test_plugin_dir_install_identifies_the_description_it_probes(tmp_path):
    co = _checkout(tmp_path)
    [entry] = tc.plugin_dir_install("plumb-line-method", str(co))
    assert {k: entry[k] for k in ("plugin", "version", "path")} == {
        "plugin": "plumb-line@inline", "version": "0.11.5", "path": str(co)}
    before = entry["frontmatter_sha256"]
    assert isinstance(before, str) and len(before) == 64
    # Same checkout, path and version: only the hash tells before from after.
    _checkout(tmp_path, description="Use when y.")
    [after] = tc.plugin_dir_install("plumb-line-method", str(co))
    assert after["frontmatter_sha256"] != before
    # The body is not the description: editing it leaves the hash alone.
    skill_md = co / "skills" / "plumb-line-method" / "SKILL.md"
    skill_md.write_text(skill_md.read_text() + "more body\n", encoding="utf-8")
    [again] = tc.plugin_dir_install("plumb-line-method", str(co))
    assert again["frontmatter_sha256"] == after["frontmatter_sha256"]
    # A checkout without the target skill yields nothing, as an absent
    # install does: probes would measure absence, not a description.
    assert tc.plugin_dir_install("plumb-line-nope", str(co)) == []


def test_init_environment_reads_plugins_and_mcp_servers():
    ev = {"type": "system", "subtype": "init",
          "plugins": [{"name": "plumb-line", "source": "plumb-line@inline"},
                      {"name": "agents-md", "source": "agents-md@builtin"}],
          "mcp_servers": [{"name": "claude.ai Notion", "status": "connected"}]}
    assert tc.init_environment(ev) == {
        "plugins": ["agents-md@builtin", "plumb-line@inline"],
        "mcp_servers": ["claude.ai Notion"]}
    assert tc.init_environment({"type": "stream_event"}) is None


def test_probe_reports_the_environment_and_the_first_skill_call(monkeypatch):
    import json

    def stream(*events):
        return [json.dumps(e).encode() + b"\n" for e in events]

    init = {"type": "system", "subtype": "init",
            "plugins": [{"name": "plumb-line", "source": "plumb-line@inline"}],
            "mcp_servers": []}
    skill = [{"type": "stream_event", "event": e} for e in (
        {"type": "content_block_start",
         "content_block": {"type": "tool_use", "name": "Skill"}},
        {"type": "content_block_delta", "delta": {
            "type": "input_json_delta",
            "partial_json": '{"skill": "plumb-line:plumb-line-method"}'}},
        {"type": "content_block_stop"})]

    class FakePopen:
        lines = []

        def __init__(self, cmd, **kw):
            self.cmd = cmd
            self.stdout = iter(FakePopen.lines)

        def kill(self):
            pass

    monkeypatch.setattr(tc.subprocess, "Popen", FakePopen)
    FakePopen.lines = stream(init, *skill)
    hit, winner, env = tc.probe("q", "plumb-line-method", "m", ".", 60, "/co")
    assert (hit, winner) == (True, "plumb-line:plumb-line-method")
    assert env == {"plugins": ["plumb-line@inline"], "mcp_servers": []}
    # A session that never starts reports no environment, not an empty one.
    FakePopen.lines = []
    assert tc.probe("q", "plumb-line-method", "m", ".", 60) == (False, None, None)


def test_environments_are_counted_per_distinct_environment():
    other = {"plugins": ["superpowers@x"], "mcp_servers": []}
    got = tc.summarise_environments([_ENV, other, _ENV, None])
    assert got["unobserved_probes"] == 1
    assert sorted(e["probes"] for e in got["observed"]) == [1, 2]


def test_validate_refuses_a_record_where_no_probe_reported_its_environment():
    payload = _payload(environments=tc.summarise_environments([None, None]))
    assert any("no probe reported" in i for i in tc.validate_results(payload))


def test_validate_flags_malformed_environments():
    for bad in ([], {"observed": []}, {"observed": [{"plugins": "x"}], "unobserved_probes": 0},
                {"observed": [{**_ENV, "probes": 0}], "unobserved_probes": 0}):
        payload = _payload(environments=bad)
        assert any("environments" in i for i in tc.validate_results(payload)), bad


def test_validate_refuses_a_v2_record_that_does_not_carry_its_environment():
    payload = _payload()
    payload["results-format"] = "v2"
    msg = next(i for i in tc.validate_results(payload) if "v2" in i)
    assert "environment" in msg


def test_validate_flags_isolation_flags_that_are_not_a_list_of_strings():
    for bad in ("--strict-mcp-config", [1], None):
        payload = _payload()
        payload["probe"]["isolation_flags"] = bad
        assert any("probe" in i for i in tc.validate_results(payload)), bad


def _run_main(monkeypatch, tmp_path, extra, installed=()):
    """Run main() with run_tier faked; return (record, the calls run_tier got)."""
    import json
    calls = []

    def fake_run_tier(evals, target, model, runs, workers, timeout, log,
                      threshold=tc.THRESHOLD, plugin_dir=None):
        calls.append({"model": model, "plugin_dir": plugin_dir})
        # The screen tier misses the should-trigger query, so the confirm
        # tier runs too and its wiring is exercised.
        rows = [{"query": e["query"], "should_trigger": e["should_trigger"],
                 "runs": [model == "confirm"], "winners": [None]} for e in evals]
        return tc.score(rows, threshold), [_ENV] * len(evals)

    monkeypatch.setattr(tc, "run_tier", fake_run_tier)
    monkeypatch.setattr(tc, "installed_locations", lambda target: list(installed))
    evals = tmp_path / "evals.json"
    evals.write_text(json.dumps([{"query": "q", "should_trigger": True}]), encoding="utf-8")
    out = tmp_path / "out.json"
    code = tc.main([str(evals), "plumb-line-method", str(out),
                    "--screen-model", "screen", "--confirm-model", "confirm", *extra])
    assert code == 0
    return json.loads(out.read_text(encoding="utf-8")), calls


def test_main_carries_the_plugin_dir_to_both_tiers_and_the_record(monkeypatch, tmp_path):
    # The #487 review's surviving mutations: a record stamped "isolated" while
    # the confirm tier probed the user's full environment.
    co = str(_checkout(tmp_path / "co"))
    record, calls = _run_main(monkeypatch, tmp_path, ["--plugin-dir", co])
    assert [c["model"] for c in calls] == ["screen", "confirm"]
    assert all(c["plugin_dir"] == co for c in calls)
    assert record["probe"]["isolation_flags"] == tc.ISOLATION_FLAGS
    assert record["probed_installs"][0]["path"] == co
    assert record["environments"]["observed"] == [{**_ENV, "probes": 2}]
    assert tc.validate_results(record) == []


def test_main_without_plugin_dir_records_no_isolation(monkeypatch, tmp_path):
    record, calls = _run_main(monkeypatch, tmp_path, [],
                              installed=[{"plugin": "o/p", "version": "9.9.9"}])
    assert all(c["plugin_dir"] is None for c in calls)
    assert record["probe"]["isolation_flags"] == []


def test_main_refuses_a_plugin_dir_that_is_not_a_directory_even_with_force(tmp_path):
    import json
    evals = tmp_path / "evals.json"
    evals.write_text(json.dumps([{"query": "q", "should_trigger": True}]), encoding="utf-8")
    code = tc.main([str(evals), "plumb-line-method", str(tmp_path / "out.json"),
                    "--plugin-dir", str(tmp_path / "missing"), "--force"])
    assert code == 2 and not (tmp_path / "out.json").exists()


def test_cli_plugin_dir_flag():
    args = tc.parse_args(["e.json", "t", "o.json", "--plugin-dir", "."])
    assert args.plugin_dir == "."
    assert tc.parse_args(["e.json", "t", "o.json"]).plugin_dir is None
