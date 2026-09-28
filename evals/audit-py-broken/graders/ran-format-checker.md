---
type: tool_used
tool: Bash
input_match: 'python[0-9.]*\s+\\?"?[^\s"]*check_report_format\.py'
min: 1
arm: with-only
---
The auditor invoked the report-format checker with a Python interpreter, as
the audit skill instructs (skills/plumb-line-audit/SKILL.md, "Validate the
report against its own contract"; the harness's deterministic pre-tag checks
in docs/release-harness.md run the same checker). This proves the call was
made, not that it succeeded: tool_used matches the call's input, never its
outcome. With-only: the checker ships in the plugin.
