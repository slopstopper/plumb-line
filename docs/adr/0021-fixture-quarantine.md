# ADR-0021: Test fixtures are quarantined opt-in per fixture, by a self-registering pytest plugin and a dependency-free vitest subpath

**Status:** Accepted · 2026-09-29 (owner decisions on GH #123)

## Context

Tests are where fake data is supposed to live, and the impossible-task spike
showed it leaking out of them (#462, recorded on #123): in 11 of 15 FX runs
that mocked the rate provider in the tests, the fake rate came out marked
`source: "real"`. #123 asked for a pytest plugin and a vitest helper that mark
fixture-constructed values `mock` and assert that no mock taint reaches a
golden output, as optional extras that leave the zero-dependency core alone.
On 2026-09-28 the owner narrowed it to fixtures in v0.12.0 and tied the
assertion to the egress guard's no-mock semantics (#120, ADR-0020).

## Decision

On 2026-09-29 the owner accepted three recommendations, recorded on #123 with
the owner's answers ("1. Opt in per fixture", "2. Automatic registration",
"3. Yes and file for follow up to be revisited and assessed"):

1. **Marking is opt-in per fixture.** `plumb_mock_fixture` (pytest, a drop-in
   for `pytest.fixture`) and `markFixture(value)` (vitest) mark one fixture's
   value `mock`. Marking every fixture automatically would also wrap temp
   paths, clients and connections and break ordinary tests.
2. **The pytest plugin registers itself** through the package's `pytest11`
   entry point and is inert unless a test uses it, rather than needing `-p`.
3. **The check takes a marked value only**, as `guard` does; walking a
   structure of marked values is to be assessed in #544.

Settled by the author under these: the check *is* `guard` with its defaults,
so it inherits `guard`'s parity (the 40 `guard` rows) and adds only a message
prefix, pinned in each language's tests. A fixture that returns an
already-marked value is an error rather than being re-marked. The JS helper
lives on its own subpath and never imports vitest: the caller registers the
matchers with `expect.extend`. The Python plugin is a module of the package
(not a separate distribution), and it is the only module that imports pytest.

## Consequences

- An adopter quarantines a fixture with one decorator or call, and asserts a
  golden output is untainted with one line, in either language.
- The package gains a pytest entry point: every pytest run in an environment
  where the package is installed loads the plugin, and so imports the
  package; an import failure in the package would fail those runs. The
  plugin defines no hooks, fixtures or options, so it changes no test's
  behaviour until a test imports from it. The entry point is named after the
  module, so registering it explicitly as well (`pytest_plugins`, `-p`) is a
  no-op rather than a clash; `-p no:plumb_line_provenance.pytest_plugin` turns
  it off.
- `assert_tainted` / `assertTainted` (and `.not.toBeUntainted()`) verify the
  opposite claim, that the taint did reach a value: they pass only when
  `guard` refuses for mock taint, so an unmarked or malformed value is not
  taken as proof. Settled by the author after review, for both languages.
- Neither helper is bundled with the Claude Code plugin: they are test
  tooling, and the bundle is the dependency-free runtime core.
- Stubbed globals and local fake servers (#520) and CI results carrying
  provenance (#521) remain out of reach of a fixture helper, as #123 said.
