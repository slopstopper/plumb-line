# JS Payments Service — Domain-Neutral Fixture

This directory is a **domain-neutral fixture** that demonstrates the plumb-line
layering discipline applied to a payments-style service. It contains two variants:

- `clean/` — follows the principles correctly; an audit should find zero violations.
- `broken/` — identical structure with exactly **three planted violations**; an
  audit should find exactly the three findings listed in `broken/VIOLATIONS.md`.

This is not a real payment system. There is no real payment logic, no network
calls, and no external dependencies. It is a minimal shape-demonstrator.

---

## Layer structure

Both variants share the same four-layer structure with one-way imports:

```
ui → engine → services → data
```

| Layer      | File                      | Role                                                                |
| ---------- | ------------------------- | ------------------------------------------------------------------- |
| `ui`       | `src/ui/checkout.js`      | Display only; imports engine, never services or data                |
| `engine`   | `src/engine/pricing.js`   | Pure calculation; reads priors from injected config                 |
| `services` | `src/services/gateway.js` | Fetch/persist boundary; returns values with provenance + confidence |
| `data`     | `src/data/rates.js`       | Static mappings; imports nothing                                    |
| config     | `config/priors.json`      | Versioned priors injected into engine                               |

---

## Key principles demonstrated

- **One-way imports:** each layer only imports from the layer below it. `data` imports nothing.
- **Provenance + confidence on outputs:** every output object carries `provenance` (a string describing how the value was derived) and `confidence` (a 0–1 score). Mock/stub data must be labelled as such, not laundered as clean truth.
- **Priors are injected config, not hardcoded constants:** the fee rate lives in `config/priors.json` and is passed into the engine — never declared as a constant inside a function body.

---

## The three planted violations in `broken/`

See `broken/VIOLATIONS.md` for the answer key. In brief:

| ID  | File                      | Violation                                                         |
| --- | ------------------------- | ----------------------------------------------------------------- |
| P2  | `src/data/rates.js`       | Upward import — data layer imports ui layer                       |
| P5  | `src/engine/pricing.js`   | Hardcoded prior — `const FEE = 0.029` instead of reading config   |
| P3  | `src/services/gateway.js` | Laundered mock data — no `provenance` or `confidence` on response |

---

## Running the syntax check

```sh
node --check clean/src/data/rates.js
node --check clean/src/engine/pricing.js
node --check clean/src/services/gateway.js
node --check clean/src/ui/checkout.js
node --check broken/src/data/rates.js
node --check broken/src/engine/pricing.js
node --check broken/src/services/gateway.js
node --check broken/src/ui/checkout.js
```

All files should parse without errors. Violations are structural/semantic, not syntax errors.
