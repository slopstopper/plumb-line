---
type: tool_used
tool: Bash
input_match: 'check_report_format\.py'
min: 1
---
The auditor must run the report-format checker, as every blind auditor does
in the manual harness (docs/release-harness.md Part 1). A report that only
claims to be checked, or says "format-validation: not run", fails this
grader: the format verdict is earned by running the checker, not by the
report's own line.
