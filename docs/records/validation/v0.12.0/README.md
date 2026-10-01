# v0.12.0 harness evidence — how it was run and scored

The evidence behind [`../v0.12.0.md`](../v0.12.0.md). That record gives the
results; this page gives the method.

## Staging

- **One fixture copy per run, outside the repository** (`scoring/stage.sh`,
  `scoring/stage-rem.sh`).
  - Each copy holds the fixture's committed files only (`git archive`).
  - Both key files are deleted, and every `violation` line is removed,
    case-insensitively.
  - Each copy was checked with `grep -ri violation`, and each was clean.
- **What the strip touched.** It removed lines only from the JS broken
  fixture's sources, which carry inline annotations. The three clean
  variants are byte-identical to what is committed.

## Dispatch

- **Agents.** All on Claude Opus 5.5:
  - nine blind auditors;
  - six remediators over three runs (at `77c8878`, `b198bd2` and `4e68837`);
  - one dogfood auditor;
  - one showcase auditor (#576).
- **Skill and plugin root.** Each agent read the checkout's skill file
  directly, with the plugin root at the worktree.
- **Blind auditors.** They got the plain prompt from `evals/*/prompt.md` and
  the declared architecture from `AUDIT-EXPECTATIONS.md` step 3, verbatim.
- **Remediators.** They got `reports/rem-input-audit-report.md` and
  `REMEDIATE-EXPECTATIONS.md`'s full pressure prompt.
- **The showcase auditor.** It ran in the repository checkout. Its answer
  key, the example's README, the earlier report and `instrumented/` were
  withheld by instruction, not by staging. Its coverage map lists only
  `toolserver.mjs` as read.

## Scoring

- **Delivered messages, captured by script.** Each run's delivered message
  was taken from its transcript by `scoring/extract.py` (#585), never
  retyped: the message of its `SubagentHandback`.
- **The reports here.** The messages are in `reports/`, unchanged except
  that local paths are replaced by placeholders (`<harness>`, `<tmp>`,
  `<home>`). The checker ran on those files.
- **Requirement 1 (Part 1b)** was scored on the transcripts:
  - `scoring/plan_first2.py`: plan text before the first edit to the copy;
  - `scoring/plan_file_first.py`: since #600, a plan-file write a step
    before the first change, and no timing claim in the final message.
- **Requirement 2** was scored on per-finding `diff -u` output, by
  `scoring/diff_results.py`.
- **The scripts' printed output** is in `scoring/outputs.txt`: positions,
  tool names and counts, with no transcript content.
- **The scripts carry placeholder paths.** They read transcripts that are
  not committed, because those hold local paths and every tool output. So
  the requirement 1 and 2 verdicts, the step numbers and the read times
  cannot be re-derived from the repository alone.
- **The scoring rules** were `AUDIT-EXPECTATIONS.md` and
  `REMEDIATE-EXPECTATIONS.md` as committed at `77c8878`, fixed before any
  result was read.

## Notes

- Several auditors' hosts refused a `.md` file for the report's temp copy,
  so they checked a `.txt` copy of the same text.
- `rem-5` and `rem-6` each read the skill once, at 21:04:17Z. The worktree
  was switched to another branch at about 21:06Z, so both validated the
  merged skill.
