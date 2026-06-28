# Python Data Pipeline — Domain-Neutral Fixture

This directory is a **domain-neutral fixture** that demonstrates the plumb-line
layering discipline applied to a data-pipeline-style service, in Python. It
contains two variants:

- `clean/` — follows the principles correctly; an audit should find zero violations.
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
