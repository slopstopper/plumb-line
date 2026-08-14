# Fit map — do you need the provenance primitives, and on what?

This document answers the question new users ask most: *"what would I use
this on?"* It is the canonical source for that answer — the
`plumb-line-adopt` skill routes from this file, and the README links here.
If your codebase matches none of the profiles below, the honest answer is
at the end, stated plainly.

Scope note: this file covers the **run-time primitives** (the
`plumb-line-provenance` library and its ecosystem adapters). The
**review-time skills** need no fit test — `plumb-line-audit` reads any
repository. The primitives earn their keep only in codebases with a
specific shape: values of mixed trustworthiness flowing through
computation that erases where they came from.

## The one-line test

> Could a value that is fake, stale, or uncertain reach an output that
> people or systems treat as true — with nothing in the code recording the
> difference?

If no path in your codebase can do that, you do not need the primitives.

## How to read a profile

Each profile gives: **signals** (what you would see in the repo or say
about it), the **failure mode** the primitives prevent, the **smallest
useful integration** (real API, minimal surface), and **what the audit
catches afterwards** — once envelopes exist, `plumb-line-audit` and
`audit_meta`/`auditMeta` have something mechanical to check.

---

## Profile 1 — external calls with mock or fallback substitutes

The common instance today is an LLM app, but the shape is any external
dependency (model API, payment gateway, third-party service) whose real
response can be replaced by a canned one on some path.

**Signals.** Calls to an LLM SDK (Anthropic, OpenAI, or similar) or other
external service with a `try/except` or `.catch` that substitutes a
canned response; a `USE_MOCK_LLM` / `USE_MOCK`-style flag; a stub
standing in for a real fetch or gateway call; recorded fixtures replayed
in development; retrieval results mixed with generated text.

**Failure mode.** The substitute is the same type as the real response.
Two calls later nothing in the program can tell them apart, and the
canned value lands in front of a user — or in a stored report — labelled
as the real thing.

**Smallest useful integration.** Mark the two branches where they diverge;
derive everything downstream.

```js
import { mark, derive, metaOf } from "plumb-line-provenance";

const reply = ok
  ? mark(completion, { source: "real", confidence: "high" })
  : mark(FALLBACK_TEXT, { source: "mock", confidence: "low" });

const rendered = derive([reply, template], (r, t) => t.format(r));
// metaOf(rendered).derivedFromMock — true on the fallback path, and no
// API exists to clear it.
```

```python
from plumb_line_provenance import mark, derive, meta_of

reply = (mark(completion, source="real", confidence="high") if ok
         else mark(FALLBACK_TEXT, source="mock", confidence="low"))
rendered = derive([reply, template], lambda r, t: t.format(r))
# meta_of(rendered)["derived_from_mock"] is True on the fallback path.
```

**What the audit catches afterwards.** A fallback branch that hand-builds
a `real` source; a render path that drops the envelope before the output
boundary; a `derivedFromMock` value exported with no opt-in.

## Profile 2 — agent-generated data pipeline

**Signals.** An agent (or a chain of them) produces data, config, code, or
reports that downstream steps consume; generated artifacts are committed
or fed into further computation; "which run produced this file?" has no
recorded answer.

**Failure mode.** Agent output is uncertainty all the way down —
plausible, unverified, and shaped exactly like human-checked data. Once it
mixes with verified inputs, the blend inherits the *look* of the verified
part. Nothing records that a number three joins back was an agent's guess.

**Smallest useful integration.** Envelope values at the agent boundary
with an honest confidence; derive through every combination step; audit at
the exit.

```python
from plumb_line_provenance import mark, derive, meta_of, audit_meta

drafted = mark(agent_row, source="symbolic", confidence="low",
               provenance="agent run 2026-08-14, unreviewed")
merged = derive([drafted, verified], combine_rows)
problems = audit_meta(meta_of(merged))   # [] or a list of named defects
```

**What the audit catches afterwards.** Agent output marked `real`;
combined values whose confidence exceeds their weakest input (impossible
via `derive` — so its presence proves a bypass); outputs with no lineage
back to the run that produced them.

## Profile 3 — dataframes with fixtures or samples near production paths

**Signals.** pandas/numpy pipelines; a `fixtures/` or `sample_data/`
directory loadable by the same code that handles production data; a
"small CSV for local dev" that the pipeline cannot distinguish from the
real feed.

**Failure mode.** A frame built from fixture rows concatenates cleanly
with a real frame. The result carries no trace of the mixture, and a
number derived partly from sample data ships in a real report.

**Smallest useful integration.** Wrap frames at load time, declare the
source honestly, and combine only through the combinators (optional
extras: `pip install "plumb-line-provenance[pandas]"`).

```python
from plumb_line_provenance.frames import PlumbDataFrame, plumb_concat

real = PlumbDataFrame(load_feed(), source="real", confidence="high")
demo = PlumbDataFrame(load_fixture(), source="mock", confidence="low")

combined = plumb_concat([real, demo])
combined.audit()   # names the taint; combined's meta has derived_from_mock=True
```

`PlumbArray` / `plumb_concatenate` / `plumb_stack` are the numpy
equivalents. Note the design is explicit combinators, not operator
overloading — a raw `pd.concat` on unwrapped values bypasses nothing
silently, because you never had envelopes on those values to lose
(ADR-0013 records the trade-off).

**What the audit catches afterwards.** `.unwrap()` early followed by raw
pandas ops on previously-enveloped data; a fixture-derived frame written
to an output path with no `derived_from_mock` check before export.

## Profile 4 — service ingesting HTTP data of mixed freshness

**Signals.** `requests`/`httpx`/`fetch` calls whose results feed
computation; caching layers or CDN responses (`Age`, `304`, stale-while-
revalidate); retry-with-cached-value logic.

**Failure mode.** A stale cached body and a fresh 200 body are
indistinguishable once parsed. Downstream math treats week-old numbers as
current.

**Smallest useful integration.** Tag at ingestion — the adapters classify
the response for you (fresh 2xx → `real`/`high`; cache signals lower it).

```js
import { taggedFetch } from "plumb-line-provenance/http";
const { value, ...meta } = await taggedFetch(url);   // envelope, not a bare body
```

```python
from plumb_line_provenance.http import tag_requests   # or tag_httpx
env = tag_requests(requests.get(url))
```

**What the audit catches afterwards.** Ingestion sites that discard the
envelope; hand-assigned `high` confidence on responses the tagger would
have classified lower.

---

## The anti-profile — when you do not need the primitives

You do not need the primitives if all of the following hold:

- every value in the system comes from one source of truth (typically one
  database), and nothing substitutes mocks, fallbacks, or samples on any
  production path;
- values are read and displayed, not combined through transformations
  that erase their origin;
- "where did this number come from?" is always answerable by reading the
  one query that produced it.

A conventional CRUD application is the common case: adding envelopes
there is ceremony with nothing to protect. Say no and move on.

Two things remain true in the anti-profile case:

- **The skills still work.** `plumb-line-audit` reviews any repository
  against the principles; `plumb-line-method` teaches them. Neither needs
  the library present.
- **The fit can change.** The day a mock, a fallback, an LLM call, or an
  agent-written artifact lands near a production path, re-read the
  matching profile above — the smallest useful integration is deliberately
  small so that adopting late is cheap.

## After the match

- Match found and you want the discipline wired in (rule file, hooks,
  boundary checks): run `plumb-line-bootstrap`.
- Want the reasoning behind the envelopes first: run `plumb-line-method`.
- Want to see what a review finds before adopting anything: run
  `plumb-line-audit` — it needs no setup.
- API details for everything quoted above: `docs/api.md` and
  `primitives/SPEC.md` in the repository.
