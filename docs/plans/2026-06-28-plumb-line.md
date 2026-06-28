# plumb-line Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `plumb-line`, a Claude Code plugin that lets a builder give any repository the discipline of epistemic honesty enforced by tooling — distilled, domain-neutral, from the Veska Index project.

**Architecture:** A plugin holding three skills (`method` = teaching, `bootstrap` = set-up, `audit` = review) that all reference a single principles document, plus two pluggable per-language enforcement adapters (JS/TS, Python) implementing a shared adapter contract. Authored markdown carries the philosophy; small Node/Python guard scripts and lint configs carry the enforcement.

**Tech Stack:** Markdown (SKILL.md + reference docs), JSON (plugin manifest), Node.js (JS adapter hooks + Vitest tests for them), Python (Python adapter hooks + pytest tests for them), ESLint `import/no-restricted-paths` (JS boundary), `import-linter` (Python boundary).

## Global Constraints

- **Zero domain vocabulary in shipped artifacts.** No astronomy/celestial/natal/ephemeris terms anywhere except clearly-labelled examples. Verbatim rule from spec.
- **The disciplines are written once** in `reference/portable-principles.md`; skills reference it, never restate it.
- **Bootstrap ships no default layers and invents no answers.** If the builder cannot name their source-truth layer, that is the finding — surface it, do not guess.
- **Parameterized enforcement** — adapters take layer names/paths/directions as generated config; no hardcoded source paths.
- **Honesty about own maturity** — non-shipped languages/features labelled `planned` per the maturity vocabulary (current / partial / mock / planned / not-implemented).
- **Two real adapters in v1** (JS/TS + Python) behind one adapter contract.
- **The 9 principles are fixed** (see spec); the spine (null results valid) and the one-line test are framing, not numbered.
- **Audit is read-only** — it reports, never auto-fixes.
- Commit after every task. Conventional-commit messages.

---

## File Structure

```
plumb-line/
  .claude-plugin/plugin.json              plugin manifest (P1)
  README.md                               what it is, who it's for, install (P1)
  skills/
    plumb-line-method/SKILL.md            teaching skill (P1)
    plumb-line-bootstrap/SKILL.md         set-up skill (P3)
    plumb-line-audit/SKILL.md             review skill (P4)
  reference/
    portable-principles.md                THE substance — thesis + 9 principles (P1)
    ruleset-template.md                   domain-neutral AGENTS-style template (P1)
  adapters/
    adapter-contract.md                   the 4 capabilities + bootstrap interface (P2)
    js/
      eslint-boundary.template.cjs        parameterized import-restriction rule (P2)
      hooks/branch-guard.mjs              block first code edit on protected branch (P2)
      hooks/pre-commit-gate.mjs           block commit if build/test/lint fail (P2)
      hooks/boundary-guard.mjs            lint touched file for boundary breaks (P2)
      hooks/__tests__/*.test.mjs          Vitest tests for the three hooks (P2)
      package.json                        adapter dev deps (vitest) (P2)
    python/
      importlinter-boundary.template.ini  parameterized import-linter contract (P2)
      hooks/branch_guard.py               block first code edit on protected branch (P2)
      hooks/pre_commit_gate.py            block commit if build/test/lint fail (P2)
      hooks/boundary_guard.py             lint touched file for boundary breaks (P2)
      hooks/test_hooks.py                 pytest tests for the three hooks (P2)
  examples/
    js-payments-service/                  clean + broken variant (P5)
    python-data-pipeline/                 clean + broken variant (P5)
  docs/
    specs/2026-06-28-plumb-line-design.md (exists)
    plans/2026-06-28-plumb-line.md        (this file)
```

---

## Phase 1 — Foundation

### Task 1: Repo scaffold + plugin manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:**
- Produces: a valid Claude Code plugin manifest that the other skills live under; `name` field = `plumb-line`.

This task is authored config + docs. Its gate is "manifest is valid JSON with required keys" — verified by a Node one-liner, not a unit test.

- [ ] **Step 1: Write the plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "plumb-line",
  "description": "Give any repository the discipline of epistemic honesty enforced by tooling: a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and rules enforced by machines rather than goodwill.",
  "version": "0.1.0",
  "author": { "name": "Aoife Okonedo Martin" }
}
```

- [ ] **Step 2: Write `.gitignore`**

```
node_modules/
__pycache__/
*.pyc
.DS_Store
.venv/
```

- [ ] **Step 3: Write `README.md`**

Write a README with these sections (prose, drawn from the spec — do NOT invent new claims):
- One-paragraph thesis: "Epistemic honesty — including the honesty of a null result — enforced by tooling and preserved across time, not vibes."
- "Who it's for" — summarize the 7 personas from the spec in 2-3 sentences (research, data/ML, AI/agents, decision-support, domain experts, solo teams, code inheritors).
- "The three skills" — one line each on method/bootstrap/audit.
- "Install" — `git clone` then add as a plugin / point Claude Code at the directory.
- "Status" — label v1 honestly: JS + Python adapters `current`; Go/Rust `planned`.

- [ ] **Step 4: Verify the manifest is valid**

Run: `node -e "const m=require('./.claude-plugin/plugin.json'); if(m.name!=='plumb-line') throw new Error('bad name'); console.log('manifest ok:', m.name, m.version)"`
Expected: `manifest ok: plumb-line 0.1.0`

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json README.md .gitignore
git commit -m "feat: scaffold plumb-line plugin manifest and README"
```

---

### Task 2: The portable principles document (the substance)

**Files:**
- Create: `reference/portable-principles.md`

**Interfaces:**
- Produces: the canonical principles text that `plumb-line-method`, `bootstrap`, and `audit` all reference. Stable anchor headings (one `##` per principle) so skills can link to them by name.

Prose deliverable. Gate = a content checklist (Step 3), enforced by a grep that finds zero domain terms.

- [ ] **Step 1: Write the document**

Create `reference/portable-principles.md` with exactly these sections, in order:

1. `# plumb-line — portable principles`
2. `## Thesis` — the thesis sentence verbatim from the spec.
3. `## The spine: a null result is a first-class outcome` — 2-3 sentences: "no structure / no effect / inconclusive" must be expressible and honored; this separates an instrument from a result-generator.
4. `## The one-line test` — *"What state produced this output, and are we preserving it honestly?"* + one sentence on using it as a gut-check before any change.
5. Nine principle sections, each its own `##` heading, each with: a one-line **statement**, a 2-3 sentence **why**, and a **find-your-version** prompt (copy the prompts verbatim from the spec's "portable principles" table):
   - `## Principle 1 — Source-truth layer`
   - `## Principle 2 — One-way layering`
   - `## Principle 3 — Confidence + provenance`
   - `## Principle 4 — Quarantined fakery`
   - `## Principle 5 — Injectable priors`
   - `## Principle 6 — Maturity vocabulary` (list the terms: current / partial / mock / planned / not-implemented)
   - `## Principle 7 — Contracted outputs`
   - `## Principle 8 — State-first lineage`
   - `## Principle 9 — Golden baseline + explain-the-drift`
6. `## Glossary` — define: source-truth layer, derived layer, provenance, confidence, quarantined data, prior, contract, lineage, baseline drift, composition root.

- [ ] **Step 2: Verify no domain vocabulary leaked in**

Run: `grep -riE 'astronom|celestial|natal|ephemeris|veska|zodiac|horoscop' reference/portable-principles.md && echo "LEAK FOUND" || echo "clean"`
Expected: `clean`

- [ ] **Step 3: Verify all required sections exist**

Run: `grep -cE '^## (Thesis|The spine|The one-line test|Principle [1-9]|Glossary)' reference/portable-principles.md`
Expected: `13` (Thesis + spine + one-line test + 9 principles + glossary)

- [ ] **Step 4: Commit**

```bash
git add reference/portable-principles.md
git commit -m "feat: add portable-principles, the single source of the discipline"
```

---

### Task 3: The domain-neutral ruleset template

**Files:**
- Create: `reference/ruleset-template.md`

**Interfaces:**
- Consumes: principle names from `portable-principles.md`.
- Produces: an `AGENTS.md`-style template with `{{PLACEHOLDER}}` tokens that `bootstrap` (Task 8) fills from the interview.

- [ ] **Step 1: Write the template**

Create `reference/ruleset-template.md`. It mirrors an AGENTS.md working-rules file but is domain-neutral and placeholder-driven. Include these placeholder tokens (double-brace) so bootstrap can string-replace them:

```markdown
# {{PROJECT_NAME}} — working rules (generated by plumb-line)

> Thesis: epistemic honesty enforced by tooling, not vibes.
> Source of these rules: plumb-line/reference/portable-principles.md

## Layers (one-way: {{LAYER_DIRECTION}})
{{LAYER_LIST}}
- The one allowed exception (composition root): {{COMPOSITION_ROOT}}

## Source-truth layer
- {{SOURCE_TRUTH_LAYER}} holds measured/ground-truth data only.
- Forbidden inside it: derived, symbolic, mock, or hardcoded-prior logic.

## Provenance + confidence
- Anything flowing downstream carries origin + confidence: {{DOWNSTREAM_ITEMS}}

## Quarantined data
- Non-real data ({{MOCK_SOURCES}}) is labelled and excluded from outputs unless explicitly opted in.

## Injectable priors
- Tunable constants are versioned config, never magic numbers: {{PRIORS}}

## Contracted outputs
- Public outputs have a versioned, validated shape: {{OUTPUT_CONTRACTS}}

## State-first lineage
- For each output, record the inputs needed to reproduce it: {{LINEAGE}}

## Golden baseline
- These derived outputs are frozen; drift must be explained: {{BASELINE}}

## Null results
- "{{NULL_RESULT_PHRASING}}" is a valid, expressible outcome.

## Enforcement
- Language/adapter: {{ADAPTER}}
- Boundary check, test gate, pre-commit gate, branch guard installed under {{HOOKS_PATH}}.
```

- [ ] **Step 2: Verify every placeholder is closed**

Run: `python3 -c "import re,sys; t=open('reference/ruleset-template.md').read(); o=t.count('{{'); c=t.count('}}'); print('open',o,'close',c); sys.exit(0 if o==c and o>0 else 1)"`
Expected: `open N close N` with matching counts (exit 0).

- [ ] **Step 3: Commit**

```bash
git add reference/ruleset-template.md
git commit -m "feat: add domain-neutral ruleset template for bootstrap"
```

---

### Task 4: The `plumb-line-method` teaching skill

**Files:**
- Create: `skills/plumb-line-method/SKILL.md`

**Interfaces:**
- Consumes: `reference/portable-principles.md`.
- Produces: a triggerable skill named `plumb-line-method`.

- [ ] **Step 1: Write the skill**

Create `skills/plumb-line-method/SKILL.md` with YAML frontmatter and body:

```markdown
---
name: plumb-line-method
description: Use when a builder wants to learn or be reminded of the plumb-line method — the discipline of epistemic honesty enforced by tooling. Teaches the thesis, the nine portable principles, the maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.
---

# The plumb-line method

Read `reference/portable-principles.md` (relative to the plugin root) and teach
from it. Do not restate the principles here — that file is the single source.

When invoked:
1. Read the principles document.
2. Give the builder the thesis and the spine (null results are valid) first.
3. Walk the nine principles only as deep as asked; lead with the one most
   relevant to what the builder is doing.
4. Always end on the one-line test as the portable gut-check.

This skill never edits files or installs anything. For setting a project up, the
builder wants plumb-line-bootstrap; for reviewing one, plumb-line-audit.
```

- [ ] **Step 2: Verify frontmatter parses and references the principles**

Run: `grep -q 'name: plumb-line-method' skills/plumb-line-method/SKILL.md && grep -q 'portable-principles.md' skills/plumb-line-method/SKILL.md && echo ok`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add skills/plumb-line-method/SKILL.md
git commit -m "feat: add plumb-line-method teaching skill"
```

---

## Phase 2 — Enforcement adapters

### Task 5: The adapter contract

**Files:**
- Create: `adapters/adapter-contract.md`

**Interfaces:**
- Produces: the contract every adapter implements, and the exact file/CLI shape `bootstrap` relies on. Defines four capabilities: **boundary check**, **test gate**, **pre-commit gate**, **branch guard**.

- [ ] **Step 1: Write the contract**

Create `adapters/adapter-contract.md` documenting, for each capability: its purpose, the file an adapter must provide, the inputs it is parameterized by, and how bootstrap installs it. Specify this concrete shape so JS and Python implement the same thing:

```markdown
# plumb-line adapter contract

An adapter makes the principles enforceable in one language. Every adapter
provides four capabilities. Bootstrap detects the project language, then copies
and parameterizes these files into the target repo.

## 1. Boundary check
- Purpose: enforce one-way layering (Principle 2).
- Provides: a config template with {{LAYERS}} / {{DIRECTION}} placeholders.
- JS: `eslint-boundary.template.cjs` (import/no-restricted-paths).
- Python: `importlinter-boundary.template.ini` (import-linter contracts).

## 2. Test gate
- Purpose: run the project's test suite as a required gate.
- Command the adapter declares: JS `npx vitest run`; Python `pytest -q`.

## 3. Pre-commit gate
- Purpose: block a commit if build/test/lint fail.
- Provides: a hook script returning non-zero to block. JS `hooks/pre-commit-gate.mjs`; Python `hooks/pre_commit_gate.py`.

## 4. Branch guard
- Purpose: block the first code edit on a protected branch.
- Provides: a hook script. JS `hooks/branch-guard.mjs`; Python `hooks/branch_guard.py`.
- Parameterized by: PROTECTED_BRANCHES (default: main), and a docs-allowlist (paths that may be edited on a protected branch).

## Hook I/O convention (shared)
- Each guard reads JSON on stdin: `{ "filePath": "...", "command": "..." }`.
- Exit 0 = allow. Exit non-zero with a message on stderr = block.
- This matches Claude Code PreToolUse hook semantics so the same scripts work as git hooks and as Claude hooks.
```

- [ ] **Step 2: Verify the four capabilities are all documented**

Run: `grep -cE '^## [1-4]\. ' adapters/adapter-contract.md`
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add adapters/adapter-contract.md
git commit -m "feat: define the plumb-line adapter contract"
```

---

### Task 6: JS adapter — guard hooks (TDD) + boundary template

**Files:**
- Create: `adapters/js/package.json`
- Create: `adapters/js/hooks/branch-guard.mjs`
- Create: `adapters/js/hooks/pre-commit-gate.mjs`
- Create: `adapters/js/hooks/boundary-guard.mjs`
- Create: `adapters/js/eslint-boundary.template.cjs`
- Test: `adapters/js/hooks/__tests__/branch-guard.test.mjs`
- Test: `adapters/js/hooks/__tests__/boundary-guard.test.mjs`

**Interfaces:**
- Produces (each hook is a module exporting a pure `decide(input, env)` plus a thin CLI wrapper):
  - `branch-guard.mjs`: `export function decide({ filePath, branch, protectedBranches, docsAllowlist }) => { allow: boolean, reason: string }`
  - `boundary-guard.mjs`: `export function decide({ filePath, layers, direction }) => { allow: boolean, reason: string }`
  - `pre-commit-gate.mjs`: `export async function decide({ runners }) => { allow: boolean, reason: string }` where `runners` is an array of `{ name, fn }` so tests inject fakes instead of spawning real builds.

This is executable behavior → real TDD. Keeping `decide()` pure (no process I/O) is what makes it testable; the CLI wrapper just reads stdin and calls `decide`.

- [ ] **Step 1: Write `package.json` for the adapter**

```json
{
  "name": "plumb-line-js-adapter",
  "private": true,
  "type": "module",
  "scripts": { "test": "vitest run" },
  "devDependencies": { "vitest": "^2.0.0" }
}
```

- [ ] **Step 2: Install + write the failing branch-guard test**

Run: `cd adapters/js && npm install`

Create `adapters/js/hooks/__tests__/branch-guard.test.mjs`:

```javascript
import { describe, it, expect } from 'vitest';
import { decide } from '../branch-guard.mjs';

const cfg = { protectedBranches: ['main'], docsAllowlist: ['docs/', 'README.md'] };

describe('branch-guard decide', () => {
  it('blocks a code edit on a protected branch', () => {
    const r = decide({ filePath: 'src/app.js', branch: 'main', ...cfg });
    expect(r.allow).toBe(false);
    expect(r.reason).toMatch(/protected branch/i);
  });

  it('allows a docs edit on a protected branch', () => {
    const r = decide({ filePath: 'docs/x.md', branch: 'main', ...cfg });
    expect(r.allow).toBe(true);
  });

  it('allows any edit on a non-protected branch', () => {
    const r = decide({ filePath: 'src/app.js', branch: 'feature/x', ...cfg });
    expect(r.allow).toBe(true);
  });
});
```

- [ ] **Step 3: Run the test, verify it fails**

Run: `cd adapters/js && npx vitest run hooks/__tests__/branch-guard.test.mjs`
Expected: FAIL — cannot resolve `../branch-guard.mjs`.

- [ ] **Step 4: Implement `branch-guard.mjs`**

```javascript
// branch-guard.mjs — block the first code edit on a protected branch.
export function decide({ filePath, branch, protectedBranches = ['main'], docsAllowlist = [] }) {
  if (!protectedBranches.includes(branch)) {
    return { allow: true, reason: 'not a protected branch' };
  }
  const isDocs = docsAllowlist.some((p) => filePath === p || filePath.startsWith(p));
  if (isDocs) return { allow: true, reason: 'docs edit allowed on protected branch' };
  return { allow: false, reason: `blocked: code edit to ${filePath} on protected branch ${branch}. Branch first.` };
}

// CLI wrapper: read {filePath} on stdin, branch from env, config from env JSON.
if (import.meta.url === `file://${process.argv[1]}`) {
  let raw = '';
  process.stdin.on('data', (d) => (raw += d));
  process.stdin.on('end', () => {
    const input = raw ? JSON.parse(raw) : {};
    const cfg = process.env.PLUMBLINE_CFG ? JSON.parse(process.env.PLUMBLINE_CFG) : {};
    const r = decide({ ...input, branch: process.env.PLUMBLINE_BRANCH, ...cfg });
    if (!r.allow) { process.stderr.write(r.reason + '\n'); process.exit(2); }
    process.exit(0);
  });
}
```

- [ ] **Step 5: Run the test, verify it passes**

Run: `cd adapters/js && npx vitest run hooks/__tests__/branch-guard.test.mjs`
Expected: PASS (3 tests).

- [ ] **Step 6: Write the failing boundary-guard test**

Create `adapters/js/hooks/__tests__/boundary-guard.test.mjs`:

```javascript
import { describe, it, expect } from 'vitest';
import { decide } from '../boundary-guard.mjs';

// layers ordered top->bottom; imports may only go downward (top imports lower).
const cfg = { layers: ['ui', 'engine', 'services', 'data'], direction: 'downward' };

describe('boundary-guard decide', () => {
  it('blocks a lower layer importing an upper layer', () => {
    const r = decide({ filePath: 'src/data/store.js', importPath: '../ui/button.js', ...cfg });
    expect(r.allow).toBe(false);
  });
  it('allows an upper layer importing a lower layer', () => {
    const r = decide({ filePath: 'src/ui/button.js', importPath: '../engine/calc.js', ...cfg });
    expect(r.allow).toBe(true);
  });
  it('allows same-layer imports', () => {
    const r = decide({ filePath: 'src/engine/a.js', importPath: './b.js', ...cfg });
    expect(r.allow).toBe(true);
  });
});
```

- [ ] **Step 7: Run it, verify it fails**

Run: `cd adapters/js && npx vitest run hooks/__tests__/boundary-guard.test.mjs`
Expected: FAIL — cannot resolve `../boundary-guard.mjs`.

- [ ] **Step 8: Implement `boundary-guard.mjs`**

```javascript
// boundary-guard.mjs — block imports that violate one-way layering.
function layerOf(path, layers) {
  return layers.find((l) => new RegExp(`(^|/)${l}(/|$)`).test(path));
}
export function decide({ filePath, importPath, layers, direction = 'downward' }) {
  const from = layerOf(filePath, layers);
  const to = layerOf(importPath, layers);
  if (!from || !to || from === to) return { allow: true, reason: 'same or unscoped layer' };
  const fromIdx = layers.indexOf(from);
  const toIdx = layers.indexOf(to);
  const ok = direction === 'downward' ? toIdx > fromIdx : toIdx < fromIdx;
  return ok
    ? { allow: true, reason: `${from} -> ${to} respects ${direction}` }
    : { allow: false, reason: `boundary break: ${from} must not import ${to} (${direction})` };
}
```

(No CLI wrapper needed for tests; bootstrap wires this into ESLint via the template below. A thin wrapper identical in shape to branch-guard's may be added, but is not required for the gate.)

- [ ] **Step 9: Run it, verify it passes**

Run: `cd adapters/js && npx vitest run`
Expected: PASS (all hook tests).

- [ ] **Step 10: Write `pre-commit-gate.mjs` (injectable runners)**

```javascript
// pre-commit-gate.mjs — block a commit if any runner fails.
export async function decide({ runners }) {
  for (const { name, fn } of runners) {
    const ok = await fn();
    if (!ok) return { allow: false, reason: `pre-commit blocked: ${name} failed` };
  }
  return { allow: true, reason: 'all gates passed' };
}
```

- [ ] **Step 11: Write the ESLint boundary template**

Create `adapters/js/eslint-boundary.template.cjs`:

```javascript
// Generated by plumb-line. Enforces one-way layering (Principle 2).
// Bootstrap replaces __ZONES__ with the project's layers.
module.exports = {
  rules: {
    'import/no-restricted-paths': ['error', { zones: __ZONES__ }],
  },
};
```

- [ ] **Step 12: Commit**

```bash
git add adapters/js
git commit -m "feat: JS adapter — branch/boundary/pre-commit guards (TDD) + eslint template"
```

---

### Task 7: Python adapter — guard hooks (TDD) + boundary template

**Files:**
- Create: `adapters/python/hooks/branch_guard.py`
- Create: `adapters/python/hooks/boundary_guard.py`
- Create: `adapters/python/hooks/pre_commit_gate.py`
- Create: `adapters/python/importlinter-boundary.template.ini`
- Test: `adapters/python/hooks/test_hooks.py`

**Interfaces:**
- Produces (mirrors the JS adapter exactly so the contract holds across languages):
  - `branch_guard.decide(file_path, branch, protected_branches, docs_allowlist) -> dict(allow, reason)`
  - `boundary_guard.decide(file_path, import_path, layers, direction) -> dict(allow, reason)`
  - `pre_commit_gate.decide(runners) -> dict(allow, reason)` where `runners` is a list of `(name, callable_returning_bool)`.

- [ ] **Step 1: Write the failing tests**

Create `adapters/python/hooks/test_hooks.py`:

```python
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import branch_guard, boundary_guard, pre_commit_gate

CFG = {"protected_branches": ["main"], "docs_allowlist": ["docs/", "README.md"]}

def test_branch_blocks_code_on_protected():
    r = branch_guard.decide(file_path="src/app.py", branch="main", **CFG)
    assert r["allow"] is False

def test_branch_allows_docs_on_protected():
    r = branch_guard.decide(file_path="docs/x.md", branch="main", **CFG)
    assert r["allow"] is True

def test_branch_allows_feature_branch():
    r = branch_guard.decide(file_path="src/app.py", branch="feature/x", **CFG)
    assert r["allow"] is True

LAYERS = {"layers": ["ui", "engine", "services", "data"], "direction": "downward"}

def test_boundary_blocks_upward_import():
    r = boundary_guard.decide(file_path="src/data/store.py", import_path="src/ui/view.py", **LAYERS)
    assert r["allow"] is False

def test_boundary_allows_downward_import():
    r = boundary_guard.decide(file_path="src/ui/view.py", import_path="src/engine/calc.py", **LAYERS)
    assert r["allow"] is True

def test_pre_commit_blocks_on_failure():
    r = pre_commit_gate.decide(runners=[("tests", lambda: False)])
    assert r["allow"] is False
```

- [ ] **Step 2: Run the tests, verify they fail**

Run: `cd adapters/python && python3 -m pytest hooks/test_hooks.py -q`
Expected: FAIL — `ModuleNotFoundError: branch_guard`.

- [ ] **Step 3: Implement `branch_guard.py`**

```python
"""branch_guard — block the first code edit on a protected branch."""
def decide(file_path, branch, protected_branches=("main",), docs_allowlist=()):
    if branch not in protected_branches:
        return {"allow": True, "reason": "not a protected branch"}
    if any(file_path == p or file_path.startswith(p) for p in docs_allowlist):
        return {"allow": True, "reason": "docs edit allowed on protected branch"}
    return {"allow": False,
            "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}
```

- [ ] **Step 4: Implement `boundary_guard.py`**

```python
"""boundary_guard — block imports that violate one-way layering."""
import re
def _layer_of(path, layers):
    for l in layers:
        if re.search(rf"(^|/){l}(/|$)", path):
            return l
    return None
def decide(file_path, import_path, layers, direction="downward"):
    src, dst = _layer_of(file_path, layers), _layer_of(import_path, layers)
    if not src or not dst or src == dst:
        return {"allow": True, "reason": "same or unscoped layer"}
    si, di = layers.index(src), layers.index(dst)
    ok = di > si if direction == "downward" else di < si
    if ok:
        return {"allow": True, "reason": f"{src} -> {dst} respects {direction}"}
    return {"allow": False, "reason": f"boundary break: {src} must not import {dst} ({direction})"}
```

- [ ] **Step 5: Implement `pre_commit_gate.py`**

```python
"""pre_commit_gate — block a commit if any runner fails."""
def decide(runners):
    for name, fn in runners:
        if not fn():
            return {"allow": False, "reason": f"pre-commit blocked: {name} failed"}
    return {"allow": True, "reason": "all gates passed"}
```

- [ ] **Step 6: Run the tests, verify they pass**

Run: `cd adapters/python && python3 -m pytest hooks/test_hooks.py -q`
Expected: PASS (6 tests).

- [ ] **Step 7: Write the import-linter boundary template**

Create `adapters/python/importlinter-boundary.template.ini`:

```ini
# Generated by plumb-line. Enforces one-way layering (Principle 2).
# Bootstrap fills the layers list, top to bottom.
[importlinter]
root_package = {{ROOT_PACKAGE}}

[importlinter:contract:layers]
name = plumb-line one-way layering
type = layers
layers =
    {{LAYERS_TOP_TO_BOTTOM}}
```

- [ ] **Step 8: Commit**

```bash
git add adapters/python
git commit -m "feat: Python adapter — branch/boundary/pre-commit guards (TDD) + import-linter template"
```

---

## Phase 3 — Bootstrap

### Task 8: The `plumb-line-bootstrap` skill

**Files:**
- Create: `skills/plumb-line-bootstrap/SKILL.md`

**Interfaces:**
- Consumes: `reference/portable-principles.md`, `reference/ruleset-template.md`, `adapters/adapter-contract.md`, and the chosen adapter's files.
- Produces: in the *target* repo — a filled ruleset file, a parameterized boundary config, and installed guard hooks.

Skill (instructions) deliverable. Gate = a self-contained dry-run checklist (Step 2) plus the real dogfood in Phase 5.

- [ ] **Step 1: Write the skill**

Create `skills/plumb-line-bootstrap/SKILL.md`:

```markdown
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
Ask the find-your-version prompts from the principles, in this order. Do NOT
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
- Copy the three guard hooks into the target repo's `.claude/guards/` (or hooks dir).
- Wire the pre-commit gate to the adapter's declared test command.
- Tell the builder exactly what was written and how to enable the hooks.

## Step 5 — Report (audit format)
List every file created/modified, the adapter used, and any unanswered prompt
left as a TODO for the builder. Label anything not done as `planned`.
```

- [ ] **Step 2: Verify the skill covers all 10 prompts and the honesty constraint**

Run: `grep -c '^[0-9]\+\.' skills/plumb-line-bootstrap/SKILL.md` (expect `>= 10`) and
`grep -qi 'HONESTY CONSTRAINT' skills/plumb-line-bootstrap/SKILL.md && echo ok`
Expected: a count of at least 10, then `ok`.

- [ ] **Step 3: Commit**

```bash
git add skills/plumb-line-bootstrap/SKILL.md
git commit -m "feat: add plumb-line-bootstrap skill"
```

---

## Phase 4 — Audit

### Task 9: The `plumb-line-audit` skill

**Files:**
- Create: `skills/plumb-line-audit/SKILL.md`

**Interfaces:**
- Consumes: `reference/portable-principles.md`.
- Produces: a read-only audit report mapping findings to violated principles.

- [ ] **Step 1: Write the skill**

Create `skills/plumb-line-audit/SKILL.md`:

```markdown
---
name: plumb-line-audit
description: Use when auditing a diff or repository against the plumb-line principles — finds laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, outputs lacking recorded lineage, and baseline drift with no explanation. Read-only: it reports, never auto-fixes.
---

# Audit against the plumb-line principles

REQUIRED READING FIRST: `reference/portable-principles.md` (plugin root).

Scope the audit to the diff if one is given, else the whole repo. For broad
sweeps, dispatch read-only subagents and keep only their findings.

## Check catalogue (each finding cites the principle it violates)
1. Laundered uncertainty (P3) — a value that lost its confidence/provenance as it flowed downstream; a mock/approximate value treated as clean truth.
2. Boundary leak (P2) — an import or call crossing layers against the declared direction; symbolic/derived/mock logic inside the source-truth layer (P1).
3. Hardcoded prior (P5) — a magic number encoding a judgment call, not injected/versioned config.
4. Overstated maturity (P6) — code or docs claiming current/done for something partial/mock/planned.
5. Missing lineage (P8) — an output stored without the inputs needed to reproduce it.
6. Unexplained drift (P9) — a changed golden-baseline value with no recorded reason.
7. Suppressed null result (spine) — a code path that cannot express "no structure/no effect/inconclusive".

## Method
- For each check, grep/read for the smell, then confirm by reading context — do
  not report on a keyword match alone.
- Default to under-claiming: if unsure a finding is real, mark it "needs review",
  not "violation".

## Report (audit format)
For each finding: file:line, the principle (Pn), one-line description, and a
suggested direction (not a patch). End with a one-line summary count. If the
repo is clean, say so plainly — a clean result is a valid result.
```

- [ ] **Step 2: Verify all 7 checks and read-only stance are present**

Run: `grep -cE '^[0-9]\.' skills/plumb-line-audit/SKILL.md` (expect `>= 7`) and
`grep -qi 'never auto-fix' skills/plumb-line-audit/SKILL.md && echo ok`
Expected: at least 7, then `ok`.

- [ ] **Step 3: Commit**

```bash
git add skills/plumb-line-audit/SKILL.md
git commit -m "feat: add plumb-line-audit skill"
```

---

## Phase 5 — Examples + dogfood validation

### Task 10: JS worked example + broken variant

**Files:**
- Create: `examples/js-payments-service/clean/` (minimal layered service)
- Create: `examples/js-payments-service/broken/` (same, with planted violations)
- Create: `examples/js-payments-service/README.md`

**Interfaces:**
- Consumes: nothing at runtime; it is a fixture for proving bootstrap + audit.
- Produces: a non-domain JS repo where audit MUST find the planted violations in `broken/` and stay quiet on `clean/`.

- [ ] **Step 1: Build the `clean/` service**

Create a tiny layered structure (no real payment logic — just shape):
- `clean/src/ui/checkout.js` (imports engine only)
- `clean/src/engine/pricing.js` (pure; reads priors from injected config)
- `clean/src/services/gateway.js` (fetch/persist boundary)
- `clean/src/data/rates.js` (static mappings)
- `clean/config/priors.json` (versioned priors)
Each output object carries `provenance` + `confidence` fields. README notes the layers.

- [ ] **Step 2: Build the `broken/` variant with labelled planted violations**

Copy `clean/` to `broken/`, then plant exactly these, each noted in `broken/VIOLATIONS.md` (the answer key):
- P2: `broken/src/data/rates.js` imports `../ui/checkout.js` (upward import).
- P5: `broken/src/engine/pricing.js` hardcodes `const FEE = 0.029` instead of reading config.
- P3: `broken/src/services/gateway.js` returns a mock amount with no `provenance`/`confidence`.

- [ ] **Step 3: Write the example README**

Explain: this is a domain-neutral fixture; `clean/` should pass audit, `broken/` should yield exactly the three findings in `VIOLATIONS.md`.

- [ ] **Step 4: Commit**

```bash
git add examples/js-payments-service
git commit -m "test: add JS payments-style example (clean + broken fixtures)"
```

---

### Task 11: Python worked example + broken variant

**Files:**
- Create: `examples/python-data-pipeline/clean/`
- Create: `examples/python-data-pipeline/broken/`
- Create: `examples/python-data-pipeline/README.md`

**Interfaces:**
- Produces: a non-domain Python repo, structured like Task 10, for proving the Python adapter path.

- [ ] **Step 1: Build the `clean/` pipeline**

- `clean/src/ui/report.py` (presents; imports engine only)
- `clean/src/engine/aggregate.py` (pure; priors injected)
- `clean/src/services/source.py` (fetch boundary)
- `clean/src/data/schema.py` (static mappings)
- `clean/config/priors.toml` (versioned priors)
Each result dict carries `provenance` + `confidence`. A result can be `None`/"no signal" (null result is expressible).

- [ ] **Step 2: Build the `broken/` variant + `VIOLATIONS.md` answer key**

Plant:
- P2: `broken/src/data/schema.py` imports `src.ui.report` (upward import).
- P5: `broken/src/engine/aggregate.py` hardcodes a threshold constant instead of reading config.
- P8: `broken/src/services/source.py` returns a computed result without recording its inputs (no lineage).

- [ ] **Step 3: Write the example README** (mirror Task 10's).

- [ ] **Step 4: Commit**

```bash
git add examples/python-data-pipeline
git commit -m "test: add Python data-pipeline example (clean + broken fixtures)"
```

---

### Task 12: Dogfood validation — prove generalization

**Files:**
- Create: `docs/dogfood-results.md`

**Interfaces:**
- Consumes: bootstrap + audit skills, both adapters, both examples.
- Produces: a recorded result proving plumb-line works on non-origin-domain repos in both languages — the project's central honesty claim.

This task is verification, not new feature code. Execute the skills against the fixtures and record what happened — honestly, including any miss.

- [ ] **Step 1: Run the boundary guards against the broken fixtures directly**

Run (JS): `cd adapters/js && node -e "import('./hooks/boundary-guard.mjs').then(m=>{const r=m.decide({filePath:'src/data/rates.js',importPath:'../ui/checkout.js',layers:['ui','engine','services','data'],direction:'downward'});console.log(r);process.exit(r.allow?1:0)})"`
Expected: `{ allow: false, ... }`, exit 0.

Run (Python): `cd adapters/python && python3 -c "import sys;sys.path.insert(0,'hooks');import boundary_guard as b;r=b.decide(file_path='src/data/schema.py',import_path='src/ui/report.py',layers=['ui','engine','services','data'],direction='downward');print(r);sys.exit(0 if not r['allow'] else 1)"`
Expected: `{'allow': False, ...}`, exit 0.

- [ ] **Step 2: Run the full adapter test suites**

Run: `cd adapters/js && npx vitest run` → all pass.
Run: `cd adapters/python && python3 -m pytest -q` → all pass.

- [ ] **Step 3: Dry-run the audit skill against each `broken/` fixture**

Following `skills/plumb-line-audit/SKILL.md` by hand (or via a dispatched agent), audit `examples/js-payments-service/broken/` and `examples/python-data-pipeline/broken/`. Confirm the findings match each fixture's `VIOLATIONS.md` answer key (3 each), and that auditing `clean/` yields none.

- [ ] **Step 4: Record results honestly**

Create `docs/dogfood-results.md`: for each language — adapter tests pass/fail, boundary guard caught the planted break (y/n), audit found exactly the planted violations (list), audit stayed quiet on clean (y/n). Note any miss as a follow-up, labelled honestly. A miss here is a real result, not a failure to hide.

- [ ] **Step 5: Commit**

```bash
git add docs/dogfood-results.md
git commit -m "test: dogfood plumb-line against JS + Python non-domain fixtures"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** thesis + 9 principles → Task 2; ruleset template → Task 3; method skill → Task 4; adapter contract → Task 5; JS adapter → Task 6; Python adapter → Task 7; bootstrap → Task 8; audit → Task 9; 2 worked examples doubling as dogfood fixtures → Tasks 10–11; domain-agnosticism proof + maturity honesty → Tasks 2 (grep gate), 12 (dogfood). "Who it's for" → README (Task 1). All spec sections mapped.
- **Placeholder scan:** no TBD/TODO-as-deliverable; every code step shows code; template placeholders are intentional `{{TOKENS}}` consumed by Task 8, not plan gaps.
- **Type consistency:** `decide(...)` signatures are identical across JS (Task 6) and Python (Task 7) and match the adapter contract (Task 5); bootstrap (Task 8) consumes the exact files Tasks 3/5/6/7 produce; audit checks (Task 9) cite the same principle numbers defined in Task 2.
```

