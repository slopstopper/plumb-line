# plumb-line Provenance Envelope — Specification

**Status:** current · **Envelope schema version:** 2 · **SPEC revision:** 1.3

This is the normative, language-neutral definition of the provenance envelope,
the conservative-combination law, and the consistency checks. Any implementation
that conforms to this document interoperates with any other, regardless of
language. The reference implementations (`primitives/js/`, `primitives/python/`)
conform; the executable definition of conformance is
[`conformance/cases.json`](conformance/cases.json), exercised in both languages
(`js/conformance.test.mjs`, `python/tests/test_conformance.py`).

The key words MUST, MUST NOT, SHOULD, MAY are used as in RFC 2119.

---

## 1. The envelope

A **provenance envelope** is a record describing the trust state of a value. It
has four required fields and several optional ones.

| Field             | Req | Type            | Meaning                                                              |
| ----------------- | --- | --------------- | ------------------------------------------------------------------- |
| `source`          | yes | enum (§2)       | Where the value came from, on the status ladder.                    |
| `confidence`      | yes | enum (§2)       | How certain, on the four-level ordinal ladder.                      |
| `derivedFromMock` | yes | boolean         | `true` if this value or any ancestor was mock-sourced.              |
| `lineage`         | yes | array of step   | One step per input captured at each combination (§4).               |
| `confidenceScore` | no  | number `[0,1]`  | Higher-resolution companion to `confidence` (§3).                   |
| `weakestSource`   | no  | enum (§2)       | Least-trustworthy `source` in the ancestry; computed by the law (§4). |
| `basis`           | no  | any             | Free-form note on the derivation; by convention, an operation label naming the transform (§4). |
| `adapter`         | no  | any             | Free-form enforcement-adapter annotation.                           |
| `provenanceVersion` | no | integer        | The `PROVENANCE_VERSION` the producer stamped; read by the audit (§5b). |

Field names are given here in `camelCase` (the canonical/JSON form). A
`snake_case` binding (`derived_from_mock`, `confidence_score`, `weakest_source`,
`provenance_version`) is permitted and is what the Python implementation uses;
the two are the same envelope under a naming convention, and
`conformance/cases.json` is authored in `camelCase` with bindings translating as
needed.

Optional fields MUST be **absent** when they have no value — an implementation
MUST NOT emit `confidenceScore: null` or `weakestSource: undefined`. Absence is
meaningful: it denotes "unknown", which is distinct from any present value.

### Envelope versioning

The envelope schema carries a version constant (`PROVENANCE_VERSION`, currently
`2`). Adding a new **optional** field is backward-compatible and MUST NOT bump
the version (`confidenceScore` and `weakestSource` were added under v1). Removing
or renaming a field, changing a field's type, or changing the combination law's
result for an existing case is a breaking change and MUST bump the version —
**except** when the prior result violated another normative section of this SPEC
(e.g. an output that §5 flags as inconsistent). Correcting a self-contradiction
to a result no conformant consumer could have relied on is a conformance fix,
not a breaking change, and MUST NOT bump the version; such fixes MUST be recorded
(CHANGELOG + an ADR) and pinned by a conformance case. The zero-input combine
correction (§3, `source` `"derived"` → `"unavailable"`) is the first such fix.

---

## 2. Ordered vocabularies

Two fields draw from ordered enumerations. Order is significant: "weakest" and
"cleaner/dirtier" comparisons are defined by position.

**`source`** — status ladder, least → most trustworthy:

```
unavailable  <  mock  <  inferred  <  fallback  <  semiReal  <  derived  <  real
```

An `inferred` value (LLM/agent-produced, no external evidence behind it) ranks
just above `mock` and below `fallback` — treated as suspect until evidenced, so
that combining it with anything else drags trust down hard. See ADR-0010.

**`confidence`** — certainty ladder, least → most certain:

```
none  <  low  <  medium  <  high
```

A value not present in a ladder is **unknown**. For `confidence`, an unknown
input MUST be treated as the weakest (`none`) by the combination law (§3) and
MUST be ignored by the audit's over-claim comparison (§5). For `source`, an
unknown value is not ranked: if any lineage step's `source` is unknown, the law
omits `weakestSource` (§3 rule 6) rather than reading it off the known steps
alone, and the audit names the step (§5, `unknown source:`) (#551).

That tolerance is for envelopes an implementation is **handed**, such as parsed
JSON or another producer's output. The combination law and the checkers MUST
NOT refuse an unknown value there; they read it as above. It does not extend to envelopes an implementation
**constructs**. `makeMeta`/`make_meta`, and every constructor built on it
(`mark`, a `derive` override), MUST refuse a `source` not in the status ladder
or a `confidence` not in the certainty ladder, with an error whose message
contains `source must be one of <the ladder, comma-separated>` or
`confidence must be one of <the ladder, comma-separated>`. Refusing means the
constructor throws (JS) or raises `ValueError` (Python); it does not return
an envelope. A numeric `confidence` (`0`, `0.8`) is refused: the number
belongs in `confidenceScore`. Added in v0.12.0 (#443, ADR-0019). Before that, an
off-ladder value was stored silently, and only `validateEnvelope` noticed a
non-string.

A `derivedFromMock` that is not a boolean is refused the same way: the
constructors, and `derive`'s override, MUST refuse it with an error whose
message contains `derivedFromMock must be a boolean`. Absent or `null`
takes the default (`true` exactly when `source` is `mock`). Added in v0.12.0
(#555, ADR-0019 amendment). It is neither read as taint nor as clean.

`source` has no default at construction of a **leaf**, an envelope with no
parents. `makeMeta`/`make_meta`, `mark`, and any wrapper built on them for a
leaf value MUST refuse when `source` is left out, with an error whose message
contains `source is required (one of <the ladder, comma-separated>)`;
`confidence` still defaults to `none`. `derive` is not a leaf constructor: its
`source` comes from the combination law (§3), so a `derive` whose override
leaves `source` out MUST NOT refuse for that reason. Added
in v0.12.0 (#177, ADR-0019 amendment). Before that, `source` defaulted to
`derived`, which is untrue of a leaf with no parents and audits as
`unreproducible` (§5).

`derive` MUST refuse an input that is not a marked value, before it applies
the function, with a `TypeError` whose message is `derive: input <position>
is not a marked value (mark it first)`, counting from 0. A marked value has
the shape the egress guard reads (§5c): in JavaScript a plain object holding
`value`, in Python a dict holding `value` and `meta`. An unmarked input has no
provenance envelope to combine, and `derive` is where values are built, so it
is kept out there. A marked value whose envelope is empty still combines, as
an unknown input the audit names (§5). `derive` also refuses `inputs` that
are not a list of values (a non-iterable, a string, a mapping), with the
message `derive: inputs must be a list of marked values`, and reads any other
iterable once, so a generator's inputs are all checked and combined. The law
itself (`combine`) still accepts any input (§3). Added in v0.12.0 (#550); before that, JavaScript combined an
unmarked object or `null` as an unknown input, and Python raised an
unrelated error.

---

## 3. The combination law

When N input envelopes are combined into one output envelope, the output MUST be
computed as follows. The law is **conservative**: the result is never more
trustworthy than its inputs, and taint can never be cleared.

1. **`derivedFromMock`** = logical OR over all inputs. An input taints if its
   `derivedFromMock` is `true` OR its `source` is `mock`. Once `true`, no
   downstream combination may set it back to `false`. Only a boolean `true`
   taints. A handed envelope can carry a `derivedFromMock` that is not a
   boolean (`0`, `""`, `"false"`, `[]`), which no constructor stores: it is
   malformed, not taint, since nothing shows it means mock, and not clean
   either. The law records it on that input's step as it is, where the
   egress guard refuses it as an invalid envelope (§5c), and it adds no
   taint to the result (#555, reversing #525's rule that it tainted).
2. **`confidence`** = the weakest (lowest-ranked) `confidence` among the inputs.
3. **`confidenceScore`** = the minimum across inputs **iff every input carries a
   valid score**; otherwise the field is omitted. A missing score is "unknown"
   and MUST NOT be dropped from the minimum — any gap omits the result.
   - This is the higher-resolution analog of rule 2, **not** error propagation.
     Narrowing uncertainty through combination requires an independence
     assumption a domain-neutral law MUST NOT bake in. The law stays at `min`.
4. **`source`** = the literal `"derived"`. Combined outputs MUST NOT be promoted
   to `real` (or any clean status) by the law itself.
5. **`lineage`** = every input's prior lineage steps, concatenated, followed by
   one new step per input (§4).
6. **`weakestSource`** = the weakest `source` across the entire resulting
   `lineage` (§4). Omitted when the lineage is empty, and when any step's
   `source` cannot be ranked (missing, `null`, off the ladder, or a step that
   is not an object): an unknown ancestor must not leave the result looking as
   clean as its known ones (#551).

The law MUST be **order-independent** for fields 1–4 and 6: permuting the inputs
MUST NOT change the result except for the order of lineage steps.

The law is **total**: any input combines, including one that is not an
envelope (a string, a number, `null`, an array) and an envelope whose
`lineage` is not an array or holds steps that are not objects (#525). An
envelope is any object read by key: in Python any `Mapping`, not only a
`dict`; in JavaScript any object, an input's fields read through the
prototype. An input that is not an envelope carries no fields: it does not
taint, its confidence reads as `none`, and it contributes no prior steps. A
`lineage` that is not an array contributes no prior steps. Prior steps are
kept whatever they are: an array step as an array, a value that is not an
object as itself, and an object step as a copy of its fields. In JavaScript
that copy includes the fields the step inherits through its prototype, so an
inherited taint flag is kept (#548). It stops short of `Object.prototype`,
which is no step's own, so a polluted global is not copied into the step.

### Combining zero inputs

A value combined from no inputs is derived from nothing, so it MUST NOT claim
`source = "derived"` — that would be a derived value with an empty `lineage`,
which §5 (condition 6) flags as unreproducible. Combining zero inputs MUST
instead yield `source = "unavailable"`, `confidence = "none"`,
`derivedFromMock = false`, `lineage = []`, with `confidenceScore` and
`weakestSource` absent. This envelope MUST audit clean.

---

## 4. Lineage steps

A **lineage step** records one input's trust state at the moment of combination.
Each new step MUST contain:

| Field             | Type    | Meaning                                          |
| ----------------- | ------- | ------------------------------------------------ |
| `id`              | string  | Content-addressed identifier (see below).        |
| `of`              | string  | `"input"` for steps minted by the law.           |
| `source`          | enum    | The input's `source` at combination time; `null` when the input has none. |
| `confidence`      | enum    | The input's `confidence` at combination time; `null` when the input has none. |
| `derivedFromMock` | boolean | Whether the input tainted (flag OR mock source). |
| `confidenceScore` | number  | Present **iff** the input carried a valid score. |

### Step ids are content-addressed (#52, ADR-0010)

`id` is `"sha256:" + first 12 hex chars` of a SHA-256 hash over the step's
canonical serialization (`stepId` / `step_id`, Task 4 of wire v2):

```
of=<of>
source=<source>
confidence=<confidence>
derivedFromMock=<"true" or "false" for a boolean, "false" if absent or null; otherwise by type, see below>
confidenceScore=<IEEE-754 binary64, big-endian, as 16 lowercase hex chars; or "-" if absent or not a valid score>
inputs=<sorted, comma-joined ids of the step's input steps>
```

The six lines are joined with `\n` (no trailing newline) and hashed as UTF-8.
An absent (or `null`) `of`, `source` or `confidence` serializes as the empty
string, and a string as itself. A handed envelope can carry another type
there, and each serializes by type, the same in every language (#525): a
boolean as `true` or `false`; a number as its IEEE-754 binary64 bit pattern,
as the score is (so `1` and `1.0` agree, and an integer too large for a double
is infinity, as a JSON parser reads it); an array as `<array>`; an object as
`<object>`. Neither language's own string conversion may be used: they write
`True`/`true`, `1.0`/`1` and `1e-07`/`1e-7` differently. A number, the score
included, is written with `-0` as `0`: JSON's `-0` is `-0` in JavaScript and
the integer `0` in Python. This serialization is not one-to-one: `true` and
`"true"`, or any two arrays, write the same line, so two handed steps can
share an id. That holds for the `derivedFromMock` line too: a step whose
flag is the string `"false"` shares an id with a clean step, and one with
`"true"` with a tainted one, though the guard refuses both malformed steps
and passes neither on their account. An id identifies a step's content for
lineage references; it is not a trust verdict, and nothing may be judged
from an id alone. The `derivedFromMock`
line is `true` or `false` for a boolean, `false` when absent or `null`, and
otherwise the malformed value the law kept (§3) serialized by type, as the
fields above are.

Input ids are sorted by Unicode code point (not by UTF-16 code unit, which
puts a character above U+FFFF before U+FFFF). Ids the law mints are ASCII,
but a handed lineage can carry any string. The text is hashed as UTF-8, with
a lone surrogate, which JSON can carry, written as U+FFFD.

The score is encoded as its raw double bit pattern, **not** as a JSON number:
JSON serializers disagree across languages for the same double (`0.00001` is
`1e-05` in Python's `json.dumps` and `0.00001` in JavaScript's
`JSON.stringify`), which would give the same step different ids. The bit
pattern is identical in every IEEE-754 language by construction.

Worked example — an input step with a score where the two JSON forms differ:

<!-- step-id worked example: {"of": "input", "source": "real", "confidence": "high", "derivedFromMock": false, "confidenceScore": 0.00001} -->
```text
of=input
source=real
confidence=high
derivedFromMock=false
confidenceScore=3ee4f8b588e368f1
inputs=
```

hashes to `sha256:fb171b6077bc`.

A second, with no score and two input ids given unsorted
(`sha256:fb171b6077bc`, `sha256:097181b20233`), so the sort and join apply:

<!-- step-id worked example: {"of": "input", "source": "fallback", "confidence": "medium", "derivedFromMock": true, "inputIds": ["sha256:fb171b6077bc", "sha256:097181b20233"]} -->
```text
of=input
source=fallback
confidence=medium
derivedFromMock=true
confidenceScore=-
inputs=sha256:097181b20233,sha256:fb171b6077bc
```

hashes to `sha256:b8a0413840c5`. `scripts/test_spec_step_id.py` checks both
examples against both reference implementations.

Two guarantees follow from this construction:

- **Stable across recombination.** A step's id is a pure function of its own
  fields plus its input ids — never of when, how many times, or alongside what
  else it is combined. `combineProvenance` MUST NOT renumber or otherwise alter
  the `id` of a lineage step it inherits from a prior envelope; only the new
  input steps it mints get fresh ids. Combining A with B never changes an id
  already present in A.
- **Dedupable, not merely unique.** Two steps collide **iff** they are the same
  derivation — identical fields *and* identical input ids. That collision is
  **intended dedup**, not an error: it means the same derivation happened twice
  (e.g. two branches recombining an identical sub-lineage), and an implementation
  MUST NOT attempt to force artificial uniqueness (e.g. via a counter or random
  suffix) — see ADR-0010 for the rejected alternatives (random UUIDs, a
  flat field-only hash with no ancestry).

`weakestSource` is **computed by the law**: it is derived from the lineage and
MUST NOT be settable as a combination override. A constructor may accept a
hand-set value (the reference implementations do), but a value cleaner than
the lineage proves MUST be flagged by the audit in §5: check 4 against the
lineage; check 8 on a value with no lineage, where a leaf's hand-set
`weakestSource` has nothing else to contradict it; and, also check 8, a
stated value over a lineage with an unknown source, which cannot be shown
(#553, #551). Until v0.12.0 this paragraph said a caller MUST NOT be able to
hand-set it, which the reference implementations never enforced.

An output whose `source` is `"derived"` MUST have a non-empty `lineage`; a
derived value with no lineage is unreproducible (§5).

### The transformation is not captured — record it in `basis`

A lineage step records each input's **trust state** at combination time, not the
**transformation** applied to produce the output. Two derivations from identical
inputs but different transforms (e.g. `sum` vs `max`) therefore produce
identically-shaped lineage. Capturing transform identity — the function, its
version, its parameters — is **out of scope for envelope schema version 2**: a
domain-neutral law cannot canonicalize an arbitrary function into a stable
identifier.

Callers who need the transform recorded for reproducibility SHOULD set the
optional `basis` field to an **operation label** — a short, stable string naming
the transform (e.g. `"pricing.applyFx@v3"`, `"aggregate.sum"`). This is a
convention, not an enforced field: the law neither writes nor validates `basis`,
and its absence is never an audit finding. It exists so that a human or a
downstream tool reading the envelope can tell *what was done*, which the lineage
alone does not say. One such tool is the baseline library (Principle 9), which
compares `basis` as a top-level field: a changed label is reported as drift
even when the value and every lineage step are unchanged.

---

## 5. Consistency checks (the audit)

An implementation MUST provide a checker (`auditMeta` / `audit_meta`) that takes
one envelope and returns a list of issue strings — empty meaning consistent. The
checker MUST detect each of the following:

| # | Issue                  | Condition                                                                                  |
| - | ---------------------- | ------------------------------------------------------------------------------------------ |
| 1 | Laundering             | a clean `source` (`real`, `semiReal`, `fallback`) with `derivedFromMock: true`.            |
| 2 | Over-claiming          | `confidence` ranked higher than the weakest `confidence` in the lineage.                   |
| 3 | Numeric over-claiming  | `confidenceScore` greater than the weakest `confidenceScore` in the lineage.               |
| 4 | Source over-claim      | `weakestSource` cleaner (higher-ranked) than the weakest `source` present in the lineage.  |
| 5 | Dropped taint          | a tainted lineage step exists (by the §3 rule) but `derivedFromMock` is `false`.           |
| 6 | Unreproducible         | `source` is `"derived"` but `lineage` is empty.                                            |
| 7 | Source over-claim      | `source` cleaner than its ancestry's weakest source: the weakest of `weakestSource` and every lineage step whose source is known (the weakest known source bounds the true one, so unknown steps cannot excuse it). A value relabelled above its ancestry (#556). `"derived"`, the law's own label, is exempt as `source`. As a floor it is exempt only when the lineage also shows a `real` step (a derive of a derive of real data); a lineage of `derived` steps alone, or a leaf stating it, shows no real data. |
| 8 | Source over-claim      | `lineage` is empty and `weakestSource` is cleaner than `source` (#553); or `weakestSource` is stated but a lineage step's source is unknown, so it cannot be shown (#551). |
| 9 | Unknown source         | a lineage step that is not an object, or whose `source` is missing, `null` or off the ladder (#551). |
| 10 | Malformed taint flag  | a lineage step whose `derivedFromMock` is not a boolean; `null` counts as absent, as at construction (§2), though the egress guard refuses a `null` step flag (#551; §3, #555). |

Checks 9 and 10 name what cannot be read instead of reading it as clean
(ADR-0014): an unknown step is not called mock, and it is not ignored. Their
messages do not quote the value, so they read the same in every language.

The checker MUST be total: a missing or malformed field MUST yield a result list
(possibly noting the problem), never an exception. A `null`/`None` envelope MUST
return a single "missing meta" issue. A checker MUST reject any input that is
not a plain object/dict without examining claims. **"Plain" means exactly the
language's own map type, not a subtype** (#165), matching the JS prototype check
(`Object.getPrototypeOf(meta) !== Object.prototype`). The rejection diagnostic
distinguishes two states (#209):

- `["missing meta"]` — `null`/`None`, a primitive, an array/list, or any
  other object outside the non-plain set below (`Map`/`Date`/class
  instances included).
- `["non-plain meta: envelope is not a plain dict/object; rebuild it with
  dict(meta) / {...meta}"]` — the container is the wrong type, though it can
  carry the envelope. The split is judged on container type alone, scoped to
  the container each language's JSON ecosystem actually produces around the
  plain type: a `dict` subclass in Python (`OrderedDict` from
  `object_pairs_hook`, `defaultdict`, a user subclass) and a null-prototype
  object in JS (pollution-safe parsers). A JS class instance stays
  `missing meta` because `JSON.parse` never yields one, not because it could
  not hold the fields. When the container did hold an envelope, the named
  rebuild MUST recover one that audits on its own claims.

Neither state can be pinned in `cases.json` — JSON has no dict-subclass or
null-prototype literal — so both are pinned by per-language unit tests. Note
that `validateEnvelope` / `validate_envelope` (§5a) is deliberately looser and
does accept subtypes; the two checkers answer different questions. Only a
plain object/dict is examined for claim consistency; a structurally empty one
(`{}`) has no claims to contradict and audits clean of every logical-consistency
check, returning only the `version-legacy:` advisory (§5b) — it also carries no
`provenanceVersion`, which the version policy treats as legacy.

### 5a. Structural validation

The audit above checks the *logic* of the claims an envelope makes and treats an
absent field as "unknown" (§2) — so a structurally empty `{}` audits clean of
every logical-consistency check (issues #1–10 above), because it asserts nothing
to contradict; its only issue is the version-legacy advisory (§5b). The audit
therefore does **not** verify that the four required fields (§1) are present.

An implementation MUST also provide a structural validator
(`validateEnvelope` / `validate_envelope`) that takes one envelope and returns a
list of issue strings — empty meaning structurally valid. It MUST detect:

- each of the four required fields (`source`, `confidence`, `derivedFromMock`,
  `lineage`) that is **absent**; and
- each required field that is **present but of the wrong type** (`source` and
  `confidence` MUST be strings, `derivedFromMock` a boolean, `lineage` an array).

Like the audit, the validator MUST be total: a `null`/`None` envelope MUST return
a single `"missing meta"` issue, and a non-object (string, number, array) MUST
return a single `"not an envelope object"` issue, never an exception. The
validator MUST NOT check enum membership of `source`/`confidence` (that is the
audit's tolerant-of-unknown domain, §2) — its sole concern is required-field
presence and type. The two checkers are complementary and independent: an
envelope MAY pass one and fail the other.

### 5b. Version field

An envelope MAY carry a `provenanceVersion` (`provenance_version` in the
`snake_case` binding) integer field recording the `PROVENANCE_VERSION` the
producer stamped it with. `combineProvenance`/`combine_provenance` and
`makeMeta`/`make_meta` MUST stamp the current `PROVENANCE_VERSION` on every
envelope they produce.

The audit (§5) MUST read this field on every call and apply an asymmetric
policy: forgiving forward, honest backward. Exactly one advisory issue is
appended (never more than one), and it never suppresses or is suppressed by any
other issue in §5's table:

| envelope `provenanceVersion` | audit issue appended |
| --- | --- |
| equal to the checker's `PROVENANCE_VERSION` (current) | none |
| greater than the checker's `PROVENANCE_VERSION` (unknown future) | `version-future: envelope version N is newer than supported <PROVENANCE_VERSION>` |
| absent, or less than the checker's `PROVENANCE_VERSION` (legacy) | `version-legacy: envelope predates version <PROVENANCE_VERSION>` |
| present but not a finite number — a string, `null`, a list, an object, a boolean, an infinity/NaN, or an integer past IEEE754 range | `version-malformed: provenance version is not a finite number` |
| a finite number with a fractional part — `1.5`, `2.5` (#216) | `version-malformed: provenance version is not an integer` |

Integrality is judged on the **value**, not the language type: JSON has no
int/float distinction, so `2.0` (a Python `float`, a JS number) is a valid
integer version. §5b's field is an integer; `1.5` is numerically comparable to
2, but "predates version 2" said of it would assert contract-conformance the
value lacks — the same reasoning that keeps `"2"` out of `version-legacy`.

**Absent and malformed are different states.** An absent field is *legacy*: the
envelope predates the field, which is a true statement about it. A field holding
`"2"` or `[]` or `true` predates nothing — reporting it as legacy would assert
something false about the producer, so it gets its own advisory. Implementations
MUST distinguish an absent key from a present `null`; a language whose map
accessor collapses the two (Python's `dict.get`) needs an explicit sentinel, and
a language whose booleans are integers (Python again) MUST exclude them here.

All three issues are **advisory only**: they MUST NOT cause the checker to throw, and
MUST NOT alter the result of any other check in §5's table. A future,
unrecognized version is accepted (not rejected) so that consumers built against
an older checker keep working against newer producers — the version field
exists to make drift *legible*, not to gate interoperability.

### 5c. The egress guard (#120, ADR-0020)

The audit reports; the **egress guard** refuses. `guard` takes a marked value
and options and either returns that value unchanged or refuses it with a list
of reasons, at the point where a value leaves the system (an export, a
display, a publish). It enforces Principle 4's mock clause, "excluded from
outputs unless explicitly opted in", at run time. A source floor the caller
sets (`minSource`, #541) lets an output point refuse more of what Principle 4
names, fallback data (source `fallback`) and inferred data (`inferred`), by
opting in, where Principle 4 asks for exclusion unless opted out. The floor
is off by default, by the owner's decision on #541. Approximate and
cached data have no rung (the HTTP adapter marks a cache hit `real` with
lower confidence), so neither can be refused specifically (#562).

**Options.** `noMock` (a boolean, default **true**), `minConfidence` (a
level on the confidence ladder, default `none`) and `minSource` (a rung on
the source ladder, default `unavailable`, which is no floor, by the owner's
decision on #541). A default of
true for `noMock` is normative: mock is excluded unless the caller opts in.
With `minSource` above `unavailable`, the guard refuses, with a reason
prefixed `source:` (`source: fallback is below the required semiReal`), when
the weakest source the ancestry shows is below it. The ancestry is the
headline `source`, `weakestSource` and every lineage step's `source`,
skipping `"derived"`, the law's own label for a computed value, so a derived
value is judged by what it was computed from. That relies on a complete
lineage, as the law builds it (§3 rule 5): a `derived` step whose own inputs
were dropped is skipped, not refused, and a fabricated envelope is outside
the threat model (N3). A floor of `"derived"` therefore behaves as `"real"`.
When nothing but `"derived"` remains, the reason is `source: no source in the
ancestry shows it meets the required <floor>`. An unknown `minSource` is a `TypeError` whose message
starts `guard: the minimum source must be one of`.

**Refusals.** A conforming guard refuses, whatever the options:

1. a value that is not a marked value (it carries no envelope): reason
   prefixed `not a marked value`;
2. a malformed envelope, with one reason per issue prefixed `invalid
   envelope:`: any §5a structural issue; a `source`, `confidence` or (when
   present) `weakestSource` off its ladder (§2); a lineage step that is not
   a plain object (a JS object literal or null-prototype object; a Python
   dict or dict subclass, judged on its contents); a step with no `source`
   (it cannot be shown not to be `mock`; the law always writes one, `null`
   when its input had none; #525); a step whose `source` or
   `confidence`, when present, is off its ladder, or whose
   `derivedFromMock`, when present, is not a boolean; or a
   `confidenceScore`, top-level or on a step, that is present and not a
   number in `[0, 1]`. The ladder and score checks are made only on an
   envelope with no §5a issue, so a structurally broken envelope reports its
   §5a issues alone. The constructors refuse off-ladder values (§2,
   ADR-0019) and the law tolerates them in a handed envelope; an output
   point fails closed; and
3. an envelope with any §5 audit issue other than the `version-legacy:` and
   `version-future:` advisories: one reason per issue, prefixed `audit:`. An
   envelope older or newer than the implementation is judged on what it
   carries, as §5b requires; `version-malformed:` is refused.

With `noMock` true it refuses, with a reason prefixed `mock:`, an envelope
with taint anywhere: `derivedFromMock` true, `source` `mock`, `weakestSource`
`mock`, or any lineage step with `derivedFromMock` true or `source` `mock`.
With `minConfidence` above `none`, it refuses, with a reason prefixed
`confidence:`, when the weakest of the top-level `confidence` and every lineage
step's `confidence` ranks below `minConfidence`. A step with no `confidence`
counts as `none` here (the audit skips it; the guard vouches only for what the
lineage states). Taint and confidence are judged from the lineage as well as
the headline fields, so a headline the lineage contradicts cannot pass.

Reasons from (3), `mock:`, `confidence:` and `source:` accumulate; (1) and (2) are
returned alone, since a missing or malformed envelope cannot be judged
further. The refusal's message is `provenance refused: ` followed by the
reasons joined with `; `.

**Programmer errors.** An unknown option, a non-boolean `noMock`, a
`minConfidence` off the confidence ladder, or a `minSource` off the source
ladder MUST raise an error, before the value is
examined, with a message starting `guard: ` (an unknown option's naming it:
`guard: unknown option <name>`). Its type MUST NOT be the refusal's type, or a
supertype or subtype of it, so a caller catching one can never catch the
other: a bad option must never be read as a refused value, or a refused value
as a bad option. Where the refusal is a subtype of a standard error callers
catch (Python's `ValueError`), the bad option's error MUST NOT be one either,
so an `except ValueError` written for refusals cannot catch it.

---

## 6. Static enforcement (review-time)

The audit (§5) checks an envelope that already exists, at run time. A **static
lint** catches the source-code patterns that *produce* inconsistent envelopes —
bypassing the combination law (§3) or laundering taint by hand — before the code
runs. It is keyed to the primitive's own functions (`mark`, `derive`,
`makeMeta`/`make_meta`, `unwrap`) and is the review-time complement to the audit.

A conforming static lint SHOULD flag the following four patterns. Each fires only
at a **resolved primitive call site** (the function is import-bound to the
primitive) and only on **literal** field values — a dynamic value cannot be
proven a violation and MUST NOT be flagged (under-claim over false positives).
The fields are an object literal in JS (`mark(v, {…})`) and keyword arguments in
Python (`mark(v, source=…)`); the rules are otherwise identical.

| ID  | Pattern                                                                                              | Run-time analog (§5) |
| --- | ---------------------------------------------------------------------------------------------------- | -------------------- |
| PB1 | a clean `source` (`real`/`semiReal`/`fallback`) asserted together with `derivedFromMock` literal `true` | laundering (#1) |
| PB2 | `derivedFromMock` literal `false` passed as a `derive` **override** (a genuine no-op the law ignores) | — |
| PB3 | a clean `source` passed as a `derive` override (relabeling a derived value)                           | laundering (#1) when there is mock taint; source over-claim (#7) whenever the source is cleaner than the ancestry, with or without mock |
| PB4 | `mark(unwrap(x), …)` — re-marking a value pulled out via the import-bound `unwrap`, dropping its lineage | unreproducible (#6) |

Reference implementations: `adapters/js/provenance-lint/` (an ESLint rule,
`no-provenance-bypass`) and `adapters/python/provenance_lint.py` (a stdlib-`ast`
checker). Both flag PB1–PB4 and stay silent on honest usage and on dynamic
values. The catalogue is intentionally **zero-false-positive**: each rule keys on
an unambiguous form, so cases needing dataflow to judge are deliberately left
out — PB2 fires only on a `derive` override (a literal `derivedFromMock:false` on
a plain `mark`/`makeMeta` is the honest stored default, not a violation), and PB4
fires only on the import-bound `unwrap(x)` (a bare `x.value` could be any raw
field). Whole-program dataflow is out of scope for envelope schema version 2.

---

## 7. Conformance

An implementation **conforms to envelope schema version 2** if, for every case in
`conformance/cases.json`:

- each `combine` case's output matches the expected fields and respects the
  declared `absent` fields,
- each `audit` case's issue list contains the expected substrings (or is empty
  when none are expected), and
- each `validate` case's issue list contains the expected substrings (or is empty
  when none are expected), and
- each `construct` case either builds an envelope with the expected fields or
  is refused with an error containing the expected substring (§2), and
- each `guard` case passes (returning the value it was given), is refused with
  reasons containing the expected substrings and none of the `expectAbsent`
  ones, or raises a programmer error containing the expected substring (§5c).

Conformance is verifiable mechanically — see [`conformance/`](conformance/) and
the report tool documented there. New behavior MUST be added to `cases.json`
(covering all languages at once) before or alongside the implementation change.

---

## 8. Reference

- Model, law, worked examples (prose): [`primitives/README.md`](README.md)
- Cross-language parity table: [`primitives/PARITY.md`](PARITY.md)
- The discipline this primitive operationalizes (Principles 3, 4, 8):
  [`reference/portable-principles.md`](../reference/portable-principles.md)
