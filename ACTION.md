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
manifest omits is simply not run — it never appears in the summary, and its
absence is never counted as a pass.

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
`PL/baseline-invalid`, `PL/ratchet-invalid`, `PL/ratchet-stale`,
`PL/tool-missing`, `PL/unparsed`.

## Usage

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@<sha>  # v7
  - uses: actions/setup-node@<sha>  # v6   (JS consumers)
  - run: npm ci                            # ESLint + the bootstrap-installed rules
  - run: pip install import-linter==2.15   # Python consumers with a boundary contract (the tested version; see Tools)
  - uses: slopstopper/plumb-line@v0.11.2
    with:
      fail-on: findings   # or none, for incremental adoption
```

Install only the toolchain your manifest actually needs — a JS-only repo
skips `pip install import-linter`, and a Python-only repo skips
`setup-node`/`npm ci` too, *unless* its manifest also carries `baselines`
(`baseline validate` needs `node`, regardless of language). The Action
brings plumb-line's own scripts from its pinned ref; your workflow provides
the language tools it runs (ADR-0016 decision 5).

The tag above is the current release; `node scripts/bump-version.mjs` rewrites
it at each release and `scripts/check-versions.mjs` fails CI if it drifts from
the manifests. Pin a release tag, or a commit sha for an immutable pin.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `manifest` | `.plumb-line/enforcement.json` | Path to the enforcement manifest, relative to `root`. |
| `root` | `.` | For monorepos: the consumer root within the checkout. The tools run there, but every result is repository-relative (`<root>/src/x.js`, resolved against `%SRCROOT%` = the checkout), and each root uploads under its own category (`plumb-line/<root>`; `plumb-line` for `.`), so two roots in one workflow never replace each other's alerts. The checkout is `github.workspace`, which is the repository root only when `actions/checkout` runs at its default `path`; a checkout under `path: app` is not a proven configuration. |
| `fail-on` | `findings` | `findings` fails the job on any error/warning result; `none` is advisory — the SARIF still uploads. Ratchet notes never count either way. |
| `sarif-file` | `${{ runner.temp }}/plumb-line.sarif` | Where the SARIF log is written. |
| `upload` | `true` | Upload to code scanning (needs `security-events: write`). `false` still writes the file. |

Required consumer permissions: `security-events: write` (to upload SARIF)
and `contents: read`.

A `root` that does not exist under the checkout fails the job immediately,
naming the missing path (`plumb-line: root '<root>' not found under the
checkout`), and writes no SARIF; one that exists but resolves outside it
(`../sibling`) fails the same way (`resolves outside the checkout`).

**Outputs**

| Output | Value | Meaning |
| --- | --- | --- |
| `sarif-file` | echoes the `sarif-file` input | The SARIF log path. |
| `summary-file` | `${{ runner.temp }}/plumb-line-summary.json` (fixed — not configurable by an input) | The summary JSON path. |
| `category` | `plumb-line`, or `plumb-line/<root>` when `root` is not `.` | The code-scanning category the SARIF uploads under. |

The summary path is fixed, so two runs of the Action in one *job* (two
roots) overwrite it: set `sarif-file` per run — the SARIF logs and the
upload categories stay distinct — and read `summary-file` knowing it is
the last run's.

The summary JSON carries its own version, `summary-format`, now **`v2`**
(#119). Two things changed from `v1`: `findings` no longer counts
note-level results (the new `notes` key counts those), and a `ratchet`
block was added — `{file, state, known, new, stale, unmeasured}`, or `null`
when the manifest names no ratchet file. A `v1` consumer that summed
`findings` sees fewer, never more, and only when a ratchet is configured;
the version moves anyway, because a changed meaning is a changed contract.

## Tools

The Action preflights each enabled capability's tool before running it. A
missing tool never silently skips the check — it becomes a `PL/tool-missing`
finding (ERROR level, uploaded like any other), the capability's state is
`tool-missing`, and **the job fails even under `fail-on: none`**: advisory
mode is about findings, never about the Action being unable to run at all
(ADR-0016, Consequences).

| Capability | Tool checked | If missing, install with |
| --- | --- | --- |
| `js.boundary` | `node_modules/.bin/eslint` (walking up from `root`; Yarn PnP has no `node_modules` and reports `tool-missing`) | `npm ci` (eslint + eslint-plugin-import-x from the consumer's package.json) |
| `js.provenance` | `node_modules/.bin/eslint` (walk-up from `root`, as above) | `npm ci` (eslint from the consumer's package.json) |
| `js.output` | `node_modules/.bin/eslint` (walk-up from `root`, as above) | `npm ci` (eslint from the consumer's package.json) |
| `python.boundary` | `lint-imports` | `pip install import-linter==2.15` (the version the text parser is tested against; unpinned installs may shift the report format ahead of this repo) |
| `python.provenance` | `python3` | `python3` on `PATH` |
| `python.output` | `python3` | `python3` on `PATH` |
| `baselines` | `node` | `node >= 22` on `PATH` |

ESLint is the consumer's own install, invoked by path — never `npx`, which
on a CI runner would download the latest ESLint from the registry when
`npm ci` was forgotten (the silent install ADR-0016 decision 5 rejects) and
would make `tool-missing` impossible to detect. The Action is tested on
`ubuntu-latest` only; the ESLint lookup is a POSIX `node_modules/.bin/eslint`
path, so Windows runners are unsupported until a run proves them (none has,
so the failure shape there is unverified: reading the code, `npm ci` on
Windows writes a shell shim at that same path, the resolver would find it,
and the orchestrator would fail trying to execute it rather than reporting
`tool-missing`).

If a `python.provenance`/`python.output` capability's globs match no files,
the tool is never invoked; the capability still reports `ran`, with a note
(`no files matched the globs`) and zero results — an empty match is not a
missing tool. The ESLint commands carry `--no-error-on-unmatched-pattern`,
so a `js.provenance`/`js.output` glob that matches no file is likewise
`ran` with zero results and the same note, where ESLint alone would exit 2:
ESLint's JSON report carries one entry per *linted* file, messages or not,
so an empty top-level array means no file was linted — no match, not a
clean surface. (`js.boundary` lints `root` itself rather than a glob list,
so it reports `eslint linted no files under root` instead.)

An empty match is a green `ran` on its own. It is **not** green when the
manifest names a ratchet and the unmeasured capability is an output
surface: see [Ratchet mode](#ratchet-mode) — a pinned surface nothing
measured fails the job regardless of `fail-on` (#395).

## Unparsed

`PL/unparsed` is the assembler's escape hatch: anything a parser cannot map
to a rule becomes a WARNING carrying the raw line, so a tool changing its
output degrades to visible noise, never to silence.

Two shapes, with different consequences:

- **One unmappable item inside an otherwise-parsed payload** — an unknown
  ESLint rule id, a malformed `provenance_lint.py` entry, an import-linter
  line the parser's grammar doesn't recognise — is a real finding. The
  capability's state stays `ran`; that one item just carries `PL/unparsed`
  instead of a mapped rule. One exception, in the direction of caution: if
  the item carries a file and the capability is an **output** surface
  (`js.output`/`python.output`), that file is one the output check never
  ran on, so the capability is `ran` but **unmeasured** — see
  [Ratchet mode](#ratchet-mode) (#392).
- **A whole payload the parser could not read at all** — empty output,
  non-JSON where JSON was expected, JSON of the wrong shape, or a text
  report with no summary line — makes the parser return exactly one
  `PL/unparsed` stand-in result. What happens to that stand-in depends on
  the exit code: if the tool also **exited non-zero**, the capability is
  `errored` and the stand-in is discarded — never written to the SARIF;
  only the tool's stderr (or stdout when stderr is empty), truncated,
  carries the tool's output, in the summary's note for that capability. If
  the tool **exited zero** despite the unreadable output, the capability is
  `ran` instead, and that same stand-in becomes an ordinary `PL/unparsed`
  finding in the SARIF. (A non-zero exit on its own never means `errored`:
  a tool that exits non-zero with a normal, parsed findings list is the
  ordinary case — real findings, never an error.) A capability the
  assembler could not make sense of at all is not a check that passed, so
  `errored` fails the job even under `fail-on: none`, the same as
  `tool-missing`.

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
is still `ran` (the parser is `partial`-maturity), never `errored`. Two
more limits of the pinned grammar: an *indirect* import chain is rendered
as one `- a -> b (l.N)` line followed by indented continuation lines for
the later links, and the parser maps only the first link — each
continuation line becomes a `PL/unparsed` warning; and the importer-to-file
mapping reads the singular `root_package` key from an ini-style config, so
a config using `root_packages` (plural) or living in `pyproject.toml`
yields results that are all `unlocated` (the module name is kept in the
message). The parser is pinned to the tested import-linter version (`2.15`:
`IMPORT_LINTER_TESTED` in `adapters/sarif/assemble.py`, held equal to the
`requirements-test.in` pin by a test), and the install hints above name
that same version; an unpinned `pip install import-linter` on a consumer's
runner could pick up a release that shifts the report format before this
repo's pin catches up. The upstream ask for a machine-readable report is
[seddonym/import-linter#291](https://github.com/seddonym/import-linter/issues/291) (tracked here as
[#376](https://github.com/slopstopper/plumb-line/issues/376); see
*Maturity*, below).

## The manifest

`.plumb-line/enforcement.json` (`enforcement-format: v1`) is the one place a
repository states which capabilities it carries. Nothing in it is a
default: a maintainer writes it by hand (`plumb-line-bootstrap` writing it
from the interview, Step 4d, is `planned`; see Maturity below). The validator is
`scripts/check_enforcement_manifest.py`; the Action refuses to run — naming
every issue — against a manifest that doesn't pass it.

```json
{
  "enforcement-format": "v1",
  "languages": ["js", "python"],
  "js": {
    "boundary": { "config": "eslint-boundary.config.cjs" },
    "provenance": { "config": "eslint-provenance.cjs",
                    "globs": ["src/**/*.mjs"],
                    "outputGlobs": ["src/pricing/**/*.mjs"] }
  },
  "python": {
    "boundary": { "config": ".importlinter" },
    "provenance": { "globs": ["src/**/*.py"],
                    "outputGlobs": ["src/pricing/**/*.py"] }
  },
  "baselines": { "dir": ".plumb-line/baselines" },
  "ratchet": { "file": ".plumb-line/ratchet.json" }
}
```

Every capability is optional — omit `boundary`, omit `provenance`, omit
`outputGlobs`, or omit `baselines`, whatever the project doesn't carry. One
exception: `languages` must always be a non-empty list naming a section
that's actually present, even for a baselines-only manifest — the
validator requires it, so a project with nothing but `baseline validate`
still declares one (possibly empty) language section. Paths (configs,
globs, `baselines.dir`) are relative to `root`.

`js.boundary.config` and `js.provenance.config` must each be a
**standalone** flat config — a complete `module.exports = [ … ]` that
registers its plugin and carries only plumb-line rules — because the Action
runs each one on its own with `--no-config-lookup`. `eslint-provenance.cjs`
as bootstrap writes it is one; the Step 4 boundary *fragment*
(`eslint-boundary.cjs`) is not — ESLint exits 2 on it alone — so the
manifest names the wrapper bootstrap writes beside it,
`eslint-boundary.config.cjs` (the shape is in the bootstrap skill, Step 4d,
and in both `examples/js-payments-service` trees). Pointing the manifest at
the consumer's full `eslint.config.*` makes every non-plumb-line rule's
finding a `PL/unparsed` warning — do not.

Validate a manifest locally, from the consumer root, with:

```bash
python3 <plumb-line checkout>/scripts/check_enforcement_manifest.py .plumb-line/enforcement.json
```

## Ratchet mode

A legacy repo cannot switch `require-provenance-output` on: every existing
untagged output fails at once. The ratchet (#119, ADR-0017) pins today's
sites and refuses only **new** ones — don't demand zero, refuse regression.

Add one key to the manifest and pin the current state:

```json
"ratchet": { "file": ".plumb-line/ratchet.json" }
```

```bash
python3 <plumb-line checkout>/adapters/sarif/ratchet.py update --because "initial pin"
git add .plumb-line/ratchet.json
```

From then on, for each `js.output` / `python.output` capability that ran:

| Site | Result |
| --- | --- |
| Pinned in the file and still reported | `PL/untagged-output` at level **note**, message prefixed `known (ratchet):`. Never fails. |
| Reported but **not** pinned | `PL/untagged-output` at level **error**; the message says how to accept it. Fails under `fail-on: findings`. |
| Pinned but no longer reported | one `PL/ratchet-stale` **note** naming the site. Never fails; `ratchet.py prune` removes it. A pinned *capability* the manifest no longer enforces at all yields the same `PL/ratchet-stale` note, one per capability — but that one is cleared by `ratchet.py update`, not `prune` (prune only shrinks site lists for capabilities still enforced). |

The head line gains `ratchet: N known, M new, S stale`, and the summary
names the file and its state. The clause appears only when the ratchet
actually ran: an invalid file prints `ratchet: invalid (checks ran
unratcheted)` rather than three zeros, and an output capability that could
not be measured adds `, U unmeasured` — three zeros over an unmeasured
surface would read as "ratcheted and clean".

**An unmeasured output surface fails the job regardless of `fail-on`**
(#395), the same class as a missing tool: the manifest pins sites on that
surface and nothing checked them, so a typo'd or stale `outputGlobs` can
never be a green job. The summary names each unmeasured capability, why it
was not measured, and the `outputGlobs` that found nothing. Without a
ratchet configured, an unmeasured capability is still an ordinary green
`ran` with zero results — there is no pinned claim to contradict.

Unmeasurability is per **file**, not per tool (#392). A file inside the
output surface that the tool could not parse — a Python syntax error, an
ESLint fatal, or a `require-provenance-output` message with no `[site: …]`
marker — is a file the output check never ran on, so the capability is
`ran` with the note `unparsed surface file: <path>` and counts as
unmeasured: the ratchet neither splits nor prunes its sites, `update` and
`prune` refuse, and a configured ratchet fails the job. Otherwise `update`
would pin a set computed as though the unreadable file held no sites, and
`prune` would drop the ones it used to hold.

When the file is invalid the
capability table also carries a synthetic `ratchet` row in state `errored`,
even though the ratchet is not a capability: that is how a file the runner
could not read fails the job the way a missing tool does.

A **site** is `<file>::<symbol>` — the enclosing exported (JS) or
module-level (Python) function, never a line number. Two returns in one
function are one site. **Renaming or moving a pinned function makes it a
new site**: fix it, or accept it with `ratchet.py update --because
"renamed X to Y"`. That is the honest cost of keying on sites rather than
counts (a count cannot tell "fixed one, added one" from "no change").

The file (`ratchet-format: v1`) is a contracted output: sorted, unique
sites per output capability, and an append-only `history` of
`{date, because, change}`. A capability key that is **absent** was never
measured; an **empty list** was measured and clean. Only two commands ever
write it:

- `ratchet.py update --because "<reason>"` — sets the sites to exactly what
  is reported now. Refuses an empty reason (the set may have grown) and
  refuses when any output capability could not be measured (tool missing,
  errored, no files matched — an empty ESLint file list counts as no match
  — or a file *inside* the surface the tool could not parse, #392): you
  cannot pin what you could not see. It is idempotent: when the
  measured sites equal what the file already pins, it writes nothing and
  reports `nothing changed`, so re-running never appends a history entry
  for a change that did not happen.
- `ratchet.py prune` — removes stale sites only, never adds; records
  `because: "prune"`. Shrinking needs no reason, but it refuses under the
  same guard as `update` when any output capability could not be measured —
  a capability the manifest has dropped entirely is left untouched (that is
  `update`'s job, since dropping a capability is a state change, not a
  shrink).

The Action **reads and never writes** the file: a rewrite in CI is never
committed, and a rewrite in a pre-commit hook lands after staging. Stale
entries are notes, not failures, until someone prunes.

Two deliberate asymmetries, so nobody "fixes" them:

- The manifest validator accepts `ratchet.file` **without** checking the
  file exists — `update` has to be able to create it. The Action is what
  fails on a missing or invalid file (`PL/ratchet-invalid`, and the job
  fails regardless of `fail-on`, as with a missing tool), and it runs the
  output checks unratcheted in that case rather than silently skipping.
- The lints themselves are ratchet-unaware. ESLint in an editor still
  shows every site as an error; the ratchet lives in the runner, once, in
  one language, with no JS/Python parity to maintain.

**Pre-commit:** point the gate at the runner — no new wiring:

```bash
PLUMBLINE_TEST_CMD="python3 <plumb-line>/adapters/sarif/run_checks.py --manifest .plumb-line/enforcement.json --sarif /dev/null --summary /dev/null --fail-on findings"
```

Proven end to end on `examples/ratchet-adoption` (Python) and
`examples/ratchet-adoption-js` (JavaScript, #393) — both run by `uses: ./`
in CI's Action matrix, `broken` and `clean`.

## Failure modes

Every outcome is a named state; nothing passes by silence.

| Situation | Behaviour |
| --- | --- |
| No manifest | Fails immediately, naming the bootstrap step that writes it and the hand-written shape. Never guesses a configuration. |
| Invalid manifest | Fails with the validator's findings, one per line — distinct from *absent*, so a corrupt file never reads as "not set up yet". |
| A needed tool missing | One `PL/tool-missing` result per capability, uploaded like any finding; job fails even under `fail-on: none`. Never counted as a clean check. |
| A tool exits non-zero and its output is unreadable | Capability is `errored`; the tool's stderr (or stdout when stderr is empty), truncated, is in the summary; job fails even under `fail-on: none`. A check that could not run is not a check that passed. |
| A tool exits non-zero with parsed findings | Normal: findings are mapped; job fails unless `fail-on: none`. |
| A capability's globs match no file | `ran`, zero results, never `errored`, with the note `no files matched the globs` — in **both** languages (`js.boundary` lints `root`, not globs, so its note reads `eslint linted no files under root`). The Python tools are not invoked at all; ESLint runs with `--no-error-on-unmatched-pattern` and returns an empty file list, which the runner reads as no match (ESLint emits one entry per *linted* file even when that file is clean, so an empty top-level array means nothing was linted). A capability with that note is `ran` but unmeasured: the ratchet neither splits nor prunes its sites, and `ratchet.py update`/`prune` refuse. |
| The manifest names a ratchet and an output capability was never measured | The job fails **even under `fail-on: none`** (#395), whether the surface went unmeasured through a missing tool, an errored tool, globs that matched no file, or a surface file that did not parse. The summary lists each unmeasured capability with its reason and its `outputGlobs`. A ratchet is a standing claim about a surface; a surface nothing ran on cannot uphold it. |
| A file inside an output surface does not parse | The file's `PL/unparsed` warning is kept (a surface file the tool could not read is not a clean file), and the capability is `ran` with the note `unparsed surface file: <path>`, which makes it **unmeasured** (#392): its sites are neither split nor pruned, `ratchet.py update`/`prune` refuse, and with a ratchet configured the job fails regardless of `fail-on`. Unmeasurability is per file, not per tool. |
| Valid manifest, zero capabilities | Job succeeds, empty SARIF run, the summary says plainly that zero checks ran — an empty green is legible as empty, never as clean. |
| Upload step fails (no `security-events: write`, code scanning off) | `continue-on-error: true` on that step ties the job's exit code to the enforcement result alone; a follow-on step emits a `::warning::` naming the permission (`security-events: write`) and the code-scanning setting as the two things to check; the SARIF file is still written and named in the summary. |
| `fail-on: none` | Findings still upload, the summary states the mode, exit 0 — unless a capability is `tool-missing` or `errored`, or a configured ratchet's output surface was never measured, which fail regardless. |
| Manifest names a ratchet file that is missing or invalid | One `PL/ratchet-invalid` error naming the problems; the output checks still run, unratcheted (every site an error); job fails even under `fail-on: none`. |
| A pinned ratchet site is no longer reported | One `PL/ratchet-stale` note per site; never fails. `ratchet.py prune` removes it. |
| A pinned ratchet capability is dropped from the manifest entirely | One `PL/ratchet-stale` note naming the capability; never fails. `ratchet.py update` clears it (not `prune`, which only shrinks sites for capabilities still enforced). |

## Maturity

- **The Action itself: `current`** — eight CI matrix cells (four fixtures ×
  `clean`/`broken`) run `uses: ./` against the planted fixtures on every pull
  request and every push to `main`, and again inside the release gate before
  anything is published.
  `js-payments-service` and `python-data-pipeline` enable only `boundary`,
  so that CI and end-to-end proof covers `js.boundary` and
  `python.boundary`; `examples/ratchet-adoption` enables
  `python.provenance`, `python.output` and `ratchet`, so that same CI covers
  those end to end too. `examples/ratchet-adoption-js` enables
  `js.provenance`, `js.output` and `ratchet`; its fixture rule only ever
  triggers `require-provenance-output`, so `js.output` and `ratchet` are the
  capabilities newly proven end to end there, while `js.provenance` runs and
  parses but detects nothing in this fixture. The two capabilities not
  proven end to end this way — `js.provenance` and `baselines` — are proven
  by unit tests over recorded tool output.
- **Uploading to a consumer's code scanning: `current` by construction** —
  the upload step delegates to the sha-pinned `github/codeql-action/upload-sarif`
  (the same action and sha the scorecard workflow uses) — but this repo's
  own CI runs the Action with `upload: "false"`, so code-scanning ingestion
  of this Action's SARIF is unproven anywhere until an adopter observes it.
- **import-linter's text parsing: `partial`** — see *Unparsed*, above; a
  machine-readable report is asked for upstream in [seddonym/import-linter#291](https://github.com/seddonym/import-linter/issues/291),
  and this parser is pinned to the tested version until then
  ([#376](https://github.com/slopstopper/plumb-line/issues/376)).
- **The bootstrap manifest step (Step 4d): `planned`** until a
  release-harness blind run proves a bootstrap run writes the file; the
  validator and the hand-written shape it targets are `current`.
- **Ratchet mode: `current`** for both `python.output` and `js.output`.
  `examples/ratchet-adoption` (Python) and `examples/ratchet-adoption-js`
  (JavaScript, #393) each carry a two-site output surface, a pinned
  `ratchet.json`, and both trees in the Action's CI matrix: `clean` reports
  `2 known, 0 new, 0 stale`, `broken` reports `1 known, 1 new, 0 stale`,
  neither leaves a capability unmeasured, and `test_end_to_end_over_the_planted_fixtures`
  asserts the same numbers from the real runner. The JS site marker — the
  rule's `[site: name]` message suffix and the assembler's `SITE_RE`
  extraction — is therefore no longer proven only by unit tests over recorded
  ESLint JSON: `examples/ratchet-adoption-js` runs the real ESLint against the
  real rule and the site keys reach the ratchet file. What is still unproven
  is the ratchet over a *mixed* JS+Python surface in one manifest, and over a
  surface large enough for rename churn to be routine.

See [ADR-0016](docs/adr/0016-action-manifest-and-sarif.md) for the five
decisions behind this design and their rejected alternatives.
