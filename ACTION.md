# plumb-line's GitHub Action

A composite GitHub Action (`action.yml`, repo root) that runs whatever
deterministic plumb-line enforcement a repository carries, assembles the
results into one SARIF 2.1.0 log, uploads it to GitHub code scanning, and
fails the job on findings. It needs no Claude session — this is the
always-on deterministic floor beneath the review-time skills. See
[ADR-0016](docs/adr/0016-action-manifest-and-sarif.md) for the five
decisions behind it.

## What it runs

The Action reads `.plumb-line/enforcement.json` (`enforcement-format: v1`)
and runs **only** what that manifest states. It ships no layers, globs, or
defaults of its own (ADR-0004; ADR-0016 decision 1): a capability the
manifest omits is not run, does not appear as a row in the summary, and is
never counted as a pass.

Seven capability keys, each optional:

| Capability | What runs |
| --- | --- |
| `js.boundary` | ESLint `import/no-restricted-paths` — one-way layering (Principle 2) |
| `js.provenance` | The `no-provenance-bypass` ESLint rule — PB1–PB4 |
| `js.output` | The `require-provenance-output` ESLint rule — declared-surface output tagging (ADR-0011) |
| `python.boundary` | `lint-imports` (import-linter) — one-way layering |
| `python.provenance` | `provenance_lint.py` — PB1–PB4 |
| `python.output` | `provenance_lint.py --require-output` — declared-surface output tagging |
| `baselines` | `baseline validate` — Principle 9 golden-baseline validity (ADR-0015) |

`js.output`/`python.output` are not separate manifest sections — they turn
on when a `provenance` block carries `outputGlobs` (see *The manifest*,
below).

Every result, from every capability, lands in one SARIF log under one rules
catalogue: `PL/boundary`, `PL/PB1`–`PL/PB4`, `PL/untagged-output`,
`PL/baseline-invalid`, `PL/tool-missing`, `PL/unparsed`.

## Usage

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@<sha>  # v7
  - uses: actions/setup-node@<sha>  # v6   (JS consumers)
  - run: npm ci                            # ESLint + the bootstrap-installed rules
  - run: pip install import-linter         # Python consumers with a boundary contract
  - uses: slopstopper/plumb-line@v0.11.0
    with:
      fail-on: findings   # or none, for incremental adoption
```

Install only the toolchain your manifest actually needs — a JS-only repo
skips `pip install import-linter`, a Python-only repo skips `setup-node` and
`npm ci`. The Action brings plumb-line's own scripts from its pinned ref;
your workflow provides the language tools it runs (ADR-0016 decision 5).

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `manifest` | `.plumb-line/enforcement.json` | Path to the enforcement manifest, relative to `root`. |
| `root` | `.` | For monorepos: the consumer root within the checkout. |
| `fail-on` | `findings` | `findings` fails the job on any result; `none` is advisory — the SARIF still uploads (the seam the ratchet, GH #119, will use). |
| `sarif-file` | `${{ runner.temp }}/plumb-line.sarif` | Where the SARIF log is written. |
| `upload` | `true` | Upload to code scanning (needs `security-events: write`). `false` still writes the file. |

Required consumer permissions: `security-events: write` (to upload SARIF)
and `contents: read`.

A `root` that doesn't resolve under the checkout fails the job immediately,
naming the missing path (`plumb-line: root '<root>' not found under the
checkout`), and writes no SARIF.

**Outputs**

| Output | Value | Meaning |
| --- | --- | --- |
| `sarif-file` | echoes the `sarif-file` input | The SARIF log path. |
| `summary-file` | `${{ runner.temp }}/plumb-line-summary.json` (fixed — not configurable by an input) | The summary JSON path. |

## Tools

The Action preflights each enabled capability's tool before running it. A
missing tool never silently skips the check — it becomes a `PL/tool-missing`
finding (ERROR level, uploaded like any other), the capability's state is
`tool-missing`, and **the job fails even under `fail-on: none`**: advisory
mode is about findings, never about the Action being unable to run at all
(ADR-0016, Consequences).

| Capability | Tool checked | If missing, install with |
| --- | --- | --- |
| `js.boundary` | `npx` | `npm ci` (eslint + eslint-plugin-import-x from the consumer's package.json) |
| `js.provenance` | `npx` | `npm ci` (eslint from the consumer's package.json) |
| `js.output` | `npx` | `npm ci` (eslint from the consumer's package.json) |
| `python.boundary` | `lint-imports` | `pip install import-linter` |
| `python.provenance` | `python3` | `python3` on `PATH` |
| `python.output` | `python3` | `python3` on `PATH` |
| `baselines` | `node` | `node >= 22` on `PATH` |

If a `python.provenance`/`python.output` capability's globs match no files,
the tool is never invoked; the capability still reports `ran`, with a note
(`no files matched the globs`) and zero results — an empty match is not a
missing tool.

## Unparsed

`PL/unparsed` is the assembler's escape hatch: anything a parser cannot map
to a rule becomes a WARNING carrying the raw line, so a tool changing its
output degrades to visible noise, never to silence.

Two shapes, with different consequences:

- **One unmappable item inside an otherwise-parsed payload** — an unknown
  ESLint rule id, a malformed `provenance_lint.py` entry, an import-linter
  line the parser's grammar doesn't recognise — is a real finding. The
  capability's state stays `ran`; that one item just carries `PL/unparsed`
  instead of a mapped rule.
- **A whole payload the parser could not read at all** — empty output,
  non-JSON where JSON was expected, JSON of the wrong shape, or a text
  report with no summary line — becomes exactly one `PL/unparsed` result
  standing in for the entire run. That, combined with a non-zero exit code,
  is what makes a capability `errored` rather than `ran`: a tool that exits
  non-zero with a normal, parsed findings list is the ordinary case: real
  findings, never an error. A capability the assembler could not make sense
  of at all is not a check that passed, so `errored` fails the job even
  under `fail-on: none`, the same as `tool-missing`.

**import-linter is `partial`.** It has no machine-readable output upstream,
so its report is parsed as text with a pinned grammar: a violation's
multi-location form (`(l.7, l.12)`) and its unresolved form (`(l.?)`) each
become their own result sharing the violation's message, and the importing
module is mapped to a file by walking the consumer's own `root_package`
config setting — a mapping that can miss (for example, namespace packages),
in which case the result carries the module name and no location, counted
under the summary's `unlocated`. A report whose `Contracts: N kept, M
broken.` line says violations exist, but whose body yields no line the
parser recognises, is treated as a discrepancy rather than silence: it
produces one `PL/unparsed` warning naming the mismatch, and the capability
is still `ran` — `partial` rather than `errored`. The parser is pinned to the tested
import-linter version; a follow-up issue tracks asking upstream for a
machine-readable report (see *Maturity*, below).

## The manifest

`.plumb-line/enforcement.json` (`enforcement-format: v1`) is the one place a
repository states which capabilities it carries. Nothing in it is a
default: `plumb-line-bootstrap` writes it from the interview (Step 4d), or a
maintainer writes it by hand. The validator is
`scripts/check_enforcement_manifest.py`; the Action refuses to run — naming
every issue — against a manifest that doesn't pass it.

```json
{
  "enforcement-format": "v1",
  "languages": ["js", "python"],
  "js": {
    "boundary": { "config": "eslint-boundary.cjs" },
    "provenance": { "config": "eslint-provenance.cjs",
                    "globs": ["src/**/*.mjs"],
                    "outputGlobs": ["src/pricing/**/*.mjs"] }
  },
  "python": {
    "boundary": { "config": ".importlinter" },
    "provenance": { "globs": ["src/**/*.py"],
                    "outputGlobs": ["src/pricing/**/*.py"] }
  },
  "baselines": { "dir": ".plumb-line/baselines" }
}
```

Every capability is optional — omit a language section entirely, omit
`provenance`, omit `outputGlobs`, or omit `baselines`, whatever the project
doesn't carry. Paths (configs, globs, `baselines.dir`) are relative to
`root`. Validate a manifest locally with:

```bash
python3 scripts/check_enforcement_manifest.py .plumb-line/enforcement.json
```

## Failure modes

Every outcome is a named state; nothing passes by silence.

| Situation | Behaviour |
| --- | --- |
| No manifest | Fails immediately, naming the bootstrap step that writes it and the hand-written shape. Never guesses a configuration. |
| Invalid manifest | Fails with the validator's findings, one per line — distinct from *absent*, so a corrupt file never reads as "not set up yet". |
| A needed tool missing | One `PL/tool-missing` result per capability, uploaded like any finding; job fails even under `fail-on: none`. Never counted as a clean check. |
| A tool crashes, or its output is unreadable | Capability is `errored`; the tool's stderr (or stdout when stderr is empty), truncated, is in the summary; job fails even under `fail-on: none`. A check that could not run is not a check that passed. |
| A tool exits non-zero with parsed findings | Normal: findings are mapped; job fails unless `fail-on: none`. |
| Valid manifest, zero capabilities | Job succeeds, empty SARIF run, the summary says plainly that zero checks ran — an empty green is legible as empty, never as clean. |
| Upload step fails (no `security-events: write`, code scanning off) | `continue-on-error: true` on that step ties the job's exit code to the enforcement result alone; the SARIF file is still written and named in the summary. |
| `fail-on: none` | Findings still upload, the summary states the mode, exit 0 — unless a capability is `tool-missing` or `errored`, which fail regardless. |

## Maturity

- **The Action itself: `current`** — four CI matrix cells (two fixtures ×
  `clean`/`broken`) run `uses: ./` against the planted fixtures and pass, on
  this branch.
- **Uploading to a consumer's code scanning: `current` by construction**
  (the same sha-pinned `upload-sarif` step this repo's own CI runs), but
  unproven outside this repo until someone adopts it.
- **import-linter's text parsing: `partial`** — see *Unparsed*, above; a
  follow-up issue tracks asking upstream for a machine-readable report and
  pins this parser to the tested version until then.
- **The bootstrap manifest step (Step 4d): `planned`** until a
  release-harness blind run proves a bootstrap run writes the file; the
  validator and the hand-written shape it targets are `current`.

See [ADR-0016](docs/adr/0016-action-manifest-and-sarif.md) for the five
decisions behind this design and their rejected alternatives.
