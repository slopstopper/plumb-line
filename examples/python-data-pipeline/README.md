# Python Data Pipeline — Domain-Neutral Fixture

This directory is a **domain-neutral fixture** that demonstrates the plumb-line
layering discipline applied to a data-pipeline-style service, in Python. It
contains two variants:

- `clean/` — follows the principles it adopts; a calibrated audit finds **zero
  violations** (it may note as an advisory that output contracts (P7) and a
  golden baseline (P9) are not adopted — an adoption gap, not a violation; see
  **Scope** below).
- `broken/` — identical structure with exactly **three planted violations**; an
  audit should find exactly the three findings listed in `broken/VIOLATIONS.md`.

This is not a real data pipeline. There are no real network calls and no external
dependencies beyond the Python standard library. It is a minimal shape-demonstrator.

---

## Layer structure

Both variants share the same four-layer structure with one-way imports:

```
ui → services → engine → data
```

| Layer      | File                      | Role                                                                                          |
| ---------- | ------------------------- | --------------------------------------------------------------------------------------------- |
| `ui`       | `src/ui/report.py`        | Display only; imports engine (downward skip past services)                                    |
| `services` | `src/services/source.py`  | Fetch/persist boundary; imports engine; returns values with provenance + confidence + lineage |
| `engine`   | `src/engine/aggregate.py` | Pure aggregation; imports data; reads threshold prior from injected config                    |
| `data`     | `src/data/schema.py`      | Static field mappings; imports nothing                                                        |
| config     | `config/priors.toml`      | Versioned priors injected into engine                                                         |

---

## Key principles demonstrated

- **One-way imports:** each layer only imports from the layer below it. `data` imports nothing.
- **Provenance + confidence on outputs:** every output dict carries `provenance` (a string describing how the value was derived) and `confidence` (a 0–1 score). Stub data is labelled as simulated, not laundered as clean truth.
- **Priors are injected config, not hardcoded constants:** the signal threshold lives in `config/priors.toml` and is passed into the engine — never declared as a constant inside a function or module body.
- **Lineage is recorded:** the service layer records the inputs used to produce a result (source name, record count, field names, config version) so any output can be traced back to the conditions that produced it.
- **Null results are expressible:** when no signal is detected (mean below threshold), the engine returns `result: None` and `signal_detected: False`. A null outcome is a valid, first-class result — not a failure.

---

## Scope — what this fixture adopts

This is a minimal **shape-demonstrator**, not a full application. It adopts only
the principles it teaches: **P2** one-way layering, **P3** provenance +
confidence on outputs, **P5** injectable priors, **P8** recorded lineage, and
the **null-result spine**.

The **service layer is the lineage-bearing output**: `services/source.py` records
the full lineage (source, record count, field names, config version). The
`ui → engine` import is an intentional downward skip past `services` (a layer
below is still one-way, documented in `src/ui/report.py`); the report is a thin
display of engine output and defers the lineage chain to the service result.

It deliberately does **not** adopt **P7** (a versioned, validated output contract
module) or **P9** (a pinned golden baseline) — both would bloat a small demo
without teaching anything new. A calibrated `plumb-line-audit` reports their
absence at most **once, as an advisory adoption gap** (a P6 maturity note), never
as a per-output violation. "Clean audits to zero violations" means zero
violations of the adopted principles above.

---

## The three planted violations in `broken/`

See `broken/VIOLATIONS.md` for the answer key. In brief:

| ID  | File                      | Violation                                                             |
| --- | ------------------------- | --------------------------------------------------------------------- |
| P2  | `src/data/schema.py`      | Upward import — data layer imports ui layer                           |
| P5  | `src/engine/aggregate.py` | Hardcoded prior — `SIGNAL_THRESHOLD = 0.65` instead of reading config |
| P8  | `src/services/source.py`  | Missing lineage — result returned without recording the inputs used   |

---

## Running the syntax check

```sh
python3 -m py_compile clean/src/data/schema.py
python3 -m py_compile clean/src/engine/aggregate.py
python3 -m py_compile clean/src/services/source.py
python3 -m py_compile clean/src/ui/report.py
python3 -m py_compile broken/src/data/schema.py
python3 -m py_compile broken/src/engine/aggregate.py
python3 -m py_compile broken/src/services/source.py
python3 -m py_compile broken/src/ui/report.py
```

All files should parse without errors. Violations are structural/semantic, not syntax errors.
