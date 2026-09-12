# adapters/sarif/test_assemble.py
"""Tests for adapters/sarif/assemble.py — the SARIF assembler (#118).

Run from the repo root:  python3 -m pytest -q adapters/sarif
"""
import json
import os

from adapters.sarif import assemble as A

_FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _fx(name):
    with open(os.path.join(_FX, name), encoding="utf-8") as fh:
        return fh.read()


def test_rules_catalogue_is_the_spec_list():
    assert sorted(A.RULES) == sorted(["PL/boundary", "PL/PB1", "PL/PB2", "PL/PB3", "PL/PB4",
                                      "PL/untagged-output", "PL/baseline-invalid",
                                      "PL/tool-missing", "PL/unparsed"])
    for rid, r in A.RULES.items():
        assert set(r) == {"name", "shortDescription", "helpUri", "level"}, rid
        assert r["level"] in ("error", "warning")
    assert A.RULES["PL/unparsed"]["level"] == "warning"


def test_parse_eslint_boundary_maps_rule_and_location():
    r = A.parse_eslint(_fx("eslint-boundary.json"), root="/repo")
    assert r == [{"ruleId": "PL/boundary", "level": "error",
                  "message": 'Unexpected path "../ui/checkout.js" imported in restricted zone.',
                  "file": "src/data/rates.js", "line": 8, "column": 38, "tool": "eslint", "parser": "json",
                  "whole": False}]


def test_parse_eslint_provenance_maps_pb_and_output():
    r = A.parse_eslint(_fx("eslint-provenance.json"), root="/repo")
    assert [x["ruleId"] for x in r] == ["PL/PB1", "PL/untagged-output"]
    assert r[0]["file"] == "src/data/load.mjs" and r[0]["line"] == 2


def test_parse_eslint_unknown_rule_is_unparsed():
    text = json.dumps([{"filePath": "/repo/a.js", "messages": [{"ruleId": "no-unused-vars", "severity": 2,
                                                                  "message": "x", "line": 1, "column": 1}]}])
    r = A.parse_eslint(text, root="/repo")
    assert r[0]["ruleId"] == "PL/unparsed" and "no-unused-vars" in r[0]["message"] and r[0]["level"] == "warning"


def test_parse_provenance_lint_maps_rules_and_parse_errors():
    r = A.parse_provenance_lint(_fx("provenance-lint.json"), root="/repo")
    assert [x["ruleId"] for x in r] == ["PL/PB1", "PL/untagged-output", "PL/unparsed"]
    assert r[0]["file"] == "src/data/load.py" and r[0]["line"] == 2 and r[0]["column"] is None
    assert r[2]["line"] is None  # line 0 from a syntax error is "unknown", not line 0


def test_parse_baseline_one_result_per_invalid_file():
    r = A.parse_baseline(_fx("baseline-validate.json"), root="/repo")
    assert [(x["ruleId"], x["file"]) for x in r] == [
        ("PL/baseline-invalid", ".plumb-line/baselines/broken.json"),
        ("PL/baseline-invalid", ".plumb-line/baselines/other-name.json")]
    assert "does not match the filename" in r[1]["message"]


def test_parse_import_linter_strips_ansi_and_maps_module_to_file(tmp_path):
    (tmp_path / "src" / "data").mkdir(parents=True)
    (tmp_path / "src" / "data" / "schema.py").write_text("", encoding="utf-8")
    r = A.parse_import_linter(_fx("import-linter-broken.txt"), root=str(tmp_path), root_package="src")
    assert r == [{"ruleId": "PL/boundary", "level": "error",
                  "message": "src.data.schema -> src.ui.report: src.data is not allowed to import src.ui",
                  "file": "src/data/schema.py", "line": 7, "column": None,
                  "tool": "import-linter", "parser": "text", "whole": False}]


def test_parse_import_linter_kept_report_is_empty():
    assert A.parse_import_linter(_fx("import-linter-kept.txt"), root="/repo", root_package="src") == []


def test_parse_import_linter_unmappable_module_keeps_the_module_name(tmp_path):
    r = A.parse_import_linter(_fx("import-linter-broken.txt"), root=str(tmp_path), root_package="src")
    assert r[0]["file"] is None and "src.data.schema" in r[0]["message"] and r[0]["line"] == 7


def test_parse_import_linter_garbled_is_unparsed():
    r = A.parse_import_linter(_fx("garbled.txt"), root="/repo", root_package="src")
    assert r == [A.unparsed("this line is not any format the assembler knows", "import-linter", whole=True)]
    assert r[0]["ruleId"] == "PL/unparsed"


def test_build_sarif_shape_and_catalogue():
    results = A.parse_eslint(_fx("eslint-boundary.json"), root="/repo") + [A.tool_missing("python.boundary", "pip install import-linter")]
    log = A.build_sarif(results, version="0.11.0")
    assert log["version"] == "2.1.0" and log["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    run = log["runs"][0]
    drv = run["tool"]["driver"]
    assert drv["name"] == "plumb-line" and drv["version"] == "0.11.0"
    assert sorted(r["id"] for r in drv["rules"]) == sorted(A.RULES)
    res = run["results"]
    assert res[0]["ruleId"] == "PL/boundary" and res[0]["level"] == "error"
    loc = res[0]["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"] == {"uri": "src/data/rates.js", "uriBaseId": "%SRCROOT%"}
    assert loc["region"] == {"startLine": 8, "startColumn": 38}
    assert res[0]["properties"] == {"tool": "eslint", "parser": "json"}
    assert "locations" not in res[1]  # a tool-missing result has no location
    assert res[0]["ruleIndex"] == [r["id"] for r in drv["rules"]].index("PL/boundary")


def test_build_sarif_region_omits_missing_line_and_column():
    r = A.parse_provenance_lint(_fx("provenance-lint.json"), root="/repo")
    log = A.build_sarif(r, version="x")
    loc = log["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert loc["region"] == {"startLine": 2}
    assert "region" not in log["runs"][0]["results"][2]["locations"][0]["physicalLocation"]


def test_build_summary_counts_by_state_and_kind():
    states = {"js.boundary": ("ran", "json", None), "js.provenance": ("not-enforced", None, None),
              "python.boundary": ("tool-missing", None, "pip install import-linter"),
              "baselines": ("errored", None, "exit 3: boom")}
    results = A.parse_import_linter(_fx("garbled.txt"), root="/repo", root_package="src") + \
        [A.tool_missing("python.boundary", "pip install import-linter")]
    s = A.build_summary(states, results, fail_on="findings", sarif_path="/tmp/x.sarif")
    assert s["summary-format"] == "v1" and s["fail_on"] == "findings" and s["sarif"] == "/tmp/x.sarif"
    assert s["capabilities"]["js.boundary"] == {"state": "ran", "results": 0, "parser": "json", "note": None}
    assert s["capabilities"]["python.boundary"]["note"] == "pip install import-linter"
    assert s["findings"] == 2 and s["unparsed"] == 1 and s["unlocated"] == 2


def test_summary_text_states_the_denominators():
    states = {"js.boundary": ("ran", "json", None), "js.provenance": ("not-enforced", None, None),
              "python.boundary": ("tool-missing", None, "x"), "baselines": ("errored", None, "y")}
    s = A.build_summary(states, [], fail_on="none", sarif_path="/tmp/x.sarif")
    text = A.summary_text(s)
    assert "1 check ran, 1 not enforced here, 1 tool missing, 1 errored; 0 findings" in text
    assert "fail-on: none" in text


# ---------- fix round 1 (task review): import-linter multi-line / structural headings ----------

def test_parse_import_linter_joins_multiple_line_numbers():
    text = ("Contracts: 0 kept, 1 broken.\n"
            "\n"
            "Broken contracts\n"
            "----------------\n"
            "\n"
            "src.data is not allowed to import src.ui:\n"
            "\n"
            "- src.data.schema -> src.ui.report (l.7, l.12)\n")
    r = A.parse_import_linter(text, root="/repo", root_package="src")
    assert [x["ruleId"] for x in r] == ["PL/boundary", "PL/boundary"]
    assert [x["line"] for x in r] == [7, 12]
    assert r[0]["message"] == r[1]["message"] == "src.data.schema -> src.ui.report: src.data is not allowed to import src.ui"


def test_parse_import_linter_unknown_line_is_none():
    text = ("Contracts: 0 kept, 1 broken.\n"
            "\n"
            "Broken contracts\n"
            "----------------\n"
            "\n"
            "src.data is not allowed to import src.ui:\n"
            "\n"
            "- src.data.schema -> src.ui.report (l.?)\n")
    r = A.parse_import_linter(text, root="/repo", root_package="src")
    assert len(r) == 1
    assert r[0]["ruleId"] == "PL/boundary" and r[0]["line"] is None


def test_parse_import_linter_two_violations_under_one_header():
    text = ("Contracts: 0 kept, 1 broken.\n"
            "\n"
            "Broken contracts\n"
            "----------------\n"
            "\n"
            "src.data is not allowed to import src.ui:\n"
            "\n"
            "- src.data.schema -> src.ui.report (l.7)\n"
            "- src.data.other -> src.ui.report (l.12)\n")
    r = A.parse_import_linter(text, root="/repo", root_package="src")
    assert [x["ruleId"] for x in r] == ["PL/boundary", "PL/boundary"]
    assert [x["line"] for x in r] == [7, 12]
    assert r[0]["message"] == "src.data.schema -> src.ui.report: src.data is not allowed to import src.ui"
    assert r[1]["message"] == "src.data.other -> src.ui.report: src.data is not allowed to import src.ui"


def test_parse_import_linter_arbitrary_contract_name_not_unparsed():
    text = ("Contracts: 0 kept, 1 broken.\n"
            "\n"
            "Broken contracts\n"
            "----------------\n"
            "\n"
            "My layers\n"
            "---------\n"
            "\n"
            "src.data is not allowed to import src.ui:\n"
            "\n"
            "- src.data.schema -> src.ui.report (l.7)\n")
    r = A.parse_import_linter(text, root="/repo", root_package="src")
    assert [x["ruleId"] for x in r] == ["PL/boundary"]
    assert not any("My layers" in x["message"] for x in r)


def test_parse_import_linter_broken_count_with_no_violations_is_unparsed():
    text = ("Contracts: 0 kept, 1 broken.\n"
            "\n"
            "Broken contracts\n"
            "----------------\n")
    r = A.parse_import_linter(text, root="/repo", root_package="src")
    assert r == [A.unparsed("Contracts: 1 broken reported but no violation line was recognised", "import-linter")]


# ---------- fix round 1: JSON parsers must be total (never [] or raise on bad shape) ----------

def test_parse_eslint_non_list_json_is_unparsed():
    r = A.parse_eslint("{}", root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_provenance_lint_non_list_json_is_unparsed():
    r = A.parse_provenance_lint("null", root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_baseline_non_dict_json_is_unparsed():
    r = A.parse_baseline("[]", root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_eslint_non_dict_entry_is_unparsed_not_raise():
    r = A.parse_eslint(json.dumps(["x"]), root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_eslint_null_messages_is_unparsed_not_raise():
    r = A.parse_eslint(json.dumps([{"messages": None}]), root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_provenance_lint_non_dict_entry_is_unparsed_not_raise():
    r = A.parse_provenance_lint(json.dumps([1]), root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_baseline_entry_missing_file_is_unparsed_not_raise():
    r = A.parse_baseline(json.dumps({"dir": "/repo/x", "files": [{"issues": ["boom"]}]}), root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


def test_parse_baseline_non_string_issues_is_unparsed_not_raise():
    r = A.parse_baseline(json.dumps({"dir": "/repo/x", "files": [{"file": "x.json", "issues": [123]}]}), root="/repo")
    assert len(r) == 1 and r[0]["ruleId"] == "PL/unparsed"


# ---------- fix round 1: minors (singular "finding") ----------

def test_summary_text_singularises_one_finding():
    states = {"js.boundary": ("ran", "json", None)}
    s = A.build_summary(states, [A.tool_missing("python.boundary", "x")], fail_on="none", sarif_path="/tmp/x.sarif")
    text = A.summary_text(s)
    assert "1 finding (" in text
    assert "1 findings" not in text
