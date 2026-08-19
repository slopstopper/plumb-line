# Run plumb-line without Claude

The plumb-line method is markdown instructions over ordinary files. Nothing in
the audit itself requires Claude Code — the skills are packaged as a Claude
plugin, but their bodies are host-neutral: required reading, a method, a report
contract, and a stdlib checker script. This page is the entry point that does
not route through the plugin shell, for any capable coding agent (#303).

**Maturity, stated plainly:** the instructions below are host-neutral by
design (`current`); a *measured* non-Claude pass of the blind-validation
protocol is `planned` — the first recorded run will be linked from
`docs/validation-results.md` when it exists. Until then, "any capable agent
can execute this" is a design claim, not a measured one.

## Run the audit

1. Read [`reference/portable-principles.md`](../reference/portable-principles.md)
   in full. It is the source of truth for the nine principles; the skills
   reference it and never restate it.
2. Follow [`skills/plumb-line-audit/SKILL.md`](../skills/plumb-line-audit/SKILL.md)
   from top to bottom, with the host substitutions below. Everything in it —
   the declared-architecture stop, the traversal plan, the presence and
   omission passes, the report format — is plain instruction over files.
3. Validate the report with
   [`scripts/check_report_format.py`](../scripts/check_report_format.py)
   (pure stdlib) before emitting it, per the skill's own earned-verdict rule.

### Host substitutions

| Where the skill says | A non-Claude host does |
| --- | --- |
| YAML frontmatter (`name:`, `description:`) | Ignore — it is the plugin shell's trigger metadata |
| "dispatch read-only subagents" | Use your host's parallel/read tooling, or read sequentially — the method does not depend on parallelism |
| "invoke `plumb-line-bootstrap`" (or any sibling skill) | Open that skill's `SKILL.md` and follow it the same way |
| "plugin root" | This repository's root (or the installed plugin's root — same files) |
| "the host's skill mechanism" | However your harness loads instructions; following the file is the mechanism |

The same pattern runs the other skills: `plumb-line-method` (pure teaching),
`plumb-line-adopt` (read-only routing; its output contract is
`routing-format: v1`), `plumb-line-remediate` (applies findings — needs file
editing), and `plumb-line-bootstrap` (installs enforcement — needs file
editing and shell access; its adapter mechanics are already agent-neutral
stdin/exit-code CLIs, see `adapters/adapter-contract.md`).

## Prove a host (the measured claim)

To show a given agent can actually execute the method — rather than assert
it — run the blind-validation protocol this repo scores Claude against:

1. Stage the fixtures with the scaffold scripts in `evals/audit-*/scaffold.sh`
   (they copy `examples/` fixtures and strip the answer keys; each verifies
   its own strip).
2. Give the agent only: the two required-reading files above, the staged
   fixture, and the declared architecture from
   [`examples/AUDIT-EXPECTATIONS.md`](../examples/AUDIT-EXPECTATIONS.md)
   protocol step 3. **Withhold the expectations file itself** — it contains
   the answer keys.
3. Score the result against the expectations tables, and the report's shape
   with `scripts/check_report_format.py`. Pass criteria are in the same file:
   all planted violations confirmed on `broken/`, zero confirmed violations
   on `clean/`, format clean.
4. Record the run — host, model, date, per-fixture results — in
   `docs/validation-results.md`. A pass from a second vendor's agent is the
   claim "not just a Claude skill", made with lineage instead of marketing.

## The library needs no agent at all

The run-time half is two zero-dependency packages, installable without any of
the above: `plumb-line-provenance` on [npm](https://www.npmjs.com/package/plumb-line-provenance)
and [PyPI](https://pypi.org/project/plumb-line-provenance/). See
[`docs/api.md`](../docs/api.md) and [`primitives/SPEC.md`](../primitives/SPEC.md);
conformance for a third-party implementation is defined by
[`primitives/conformance/cases.json`](../primitives/conformance/cases.json).
