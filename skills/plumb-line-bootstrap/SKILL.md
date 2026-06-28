---
name: plumb-line-bootstrap
description: Use when setting up a project with the plumb-line discipline — interviews the builder to find their source-truth layer and layering, generates a domain-neutral ruleset, and installs parameterized enforcement (boundary check, test gate, pre-commit gate, branch guard) for the project's language. Ships no default layers and invents no answers.
---

# Bootstrap a project with plumb-line

REQUIRED READING FIRST: `reference/portable-principles.md` and
`adapters/adapter-contract.md` (plugin root).

## Step 1 — Detect language, pick the adapter

- Look for `package.json` -> JS adapter (`adapters/js`).
- Look for `pyproject.toml` / `setup.py` / `requirements.txt` -> Python adapter (`adapters/python`).
- If both or neither, ASK the builder which to use. Never guess silently.

## Step 2 — Interview (one question at a time)

Ask the find-your-version prompts from the principles, in this order (ask one, wait for the answer, then proceed). Do NOT
supply defaults; these answers are the builder's, not yours:

1. Layers, top to bottom, and the one-way direction.
2. The source-truth layer, and what must never leak into it.
3. The one allowed exception (composition root), if any.
4. What flows downstream (gets provenance + confidence).
5. Where non-real (mock/fallback/cached) data is used.
6. Which constants encode judgment calls (priors to lift to config).
7. Public output shapes that need a versioned contract.
8. For each key output, the inputs needed to reproduce it.
9. Which derived outputs to freeze as a golden baseline.
10. The phrasing for a valid null result in this domain.

HONESTY CONSTRAINT: if the builder cannot name a source-truth layer, stop and
say so — that absence is the finding. Do not fabricate one.

## Step 3 — Generate the ruleset

Fill `reference/ruleset-template.md` placeholders with the answers; write it to
the target repo as `AGENTS.md` (or append if one exists — never overwrite silently).

## Step 4 — Install enforcement (from the chosen adapter)

- Copy the boundary config template, replacing layer placeholders with the
  builder's layers/direction. (JS: eslint zones; Python: import-linter layers.)
- Copy the boundary config template and the two guard hook scripts (branch guard + pre-commit gate) into the target repo's `.claude/guards/` (or hooks dir).
- Wire the pre-commit gate to the adapter's declared test command.
- Tell the builder exactly what was written and how to enable the hooks (register them in the target repo's `.claude/settings.json` as PreToolUse hooks, per the adapter contract's hook I/O convention).

## Step 5 — Report (audit format)

List every file created/modified, the adapter used, and any unanswered prompt
left as a TODO for the builder. Label anything not done as `planned`.
