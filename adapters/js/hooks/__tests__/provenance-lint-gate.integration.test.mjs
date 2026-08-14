/**
 * Integration test: prove the SHIPPED require-provenance-output rule actually
 * blocks a commit through hooks/pre-commit-gate.
 *
 * `provenance-lint/README.md` claims the rule "drops straight into
 * `hooks/pre-commit-gate` as a runner". Python pinned that claim end-to-end
 * (adapters/python/hooks/test_hooks.py::test_gate_blocks_on_untagged_output);
 * JS did not, so the README implied a demonstrated symmetry that was never
 * actually demonstrated on this side — issue #163.
 *
 * This is the JS mirror: real files on disk, the real plugin, the real gate.
 */

import { describe, it, expect, afterAll } from "vitest";
import { ESLint } from "eslint";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { decide } from "../pre-commit-gate.mjs";

const require = createRequire(import.meta.url);
// The shipped plugin entry a host project would register, not a hand-built rule
// object — so this test fails if the plugin wiring itself regresses.
const plugin = require("../../provenance-lint/index.cjs");

const RULE = "plumb-line/require-provenance-output";
// `plumb-line-provenance` matches the rule's built-in PRIMITIVE_SOURCE regex,
// which is how the rule learns that the local names `mark`/`derive` are the
// tracked primitive. It is NOT what puts the file in scope — scope is the set
// of files the config enables the rule on, and an untagged output is flagged
// with no import present at all.
const IMPORT = `import { mark, derive } from "plumb-line-provenance";\n`;

const workdir = mkdtempSync(path.join(tmpdir(), "plumb-gate-"));
afterAll(() => rmSync(workdir, { recursive: true, force: true }));

function writeSource(name, body) {
  const file = path.join(workdir, name);
  writeFileSync(file, IMPORT + body + "\n");
  return file;
}

async function lintFile(file) {
  const eslint = new ESLint({
    cwd: workdir,
    overrideConfigFile: true,
    overrideConfig: [
      {
        languageOptions: { ecmaVersion: 2022, sourceType: "module" },
        plugins: { "plumb-line": plugin },
        rules: { [RULE]: "error" },
      },
    ],
  });
  return eslint.lintFiles([file]);
}

/**
 * A runner in the exact shape hooks/pre-commit-gate expects: an async thunk
 * returning true on success. This is the wiring the README describes.
 */
function lintRunner(file) {
  return async () => {
    const results = await lintFile(file);
    return results.every((r) => r.errorCount === 0);
  };
}

describe("require-provenance-output wired into pre-commit-gate", () => {
  it("blocks the commit when an exported function returns an untagged computation", async () => {
    const file = writeSource(
      "untagged.mjs",
      `export function f(x, r) { return x * r; }`,
    );

    // Guard: prove it is OUR rule that fired, not a parse error or some other
    // rule. Without this, a typo in the fixture would still "block" and the
    // test would pass for the wrong reason.
    const results = await lintFile(file);
    const messages = results.flatMap((r) => r.messages);
    expect(messages.map((m) => m.ruleId)).toContain(RULE);

    const r = await decide({
      runners: [{ name: "require-provenance-output", fn: lintRunner(file) }],
    });

    expect(r.allow).toBe(false);
    expect(r.reason).toContain("require-provenance-output");
  });

  it("allows the commit when the output carries provenance", async () => {
    const file = writeSource(
      "tagged.mjs",
      `export function f(x, r) { return derive([x, r], (p, q) => p * q); }`,
    );

    const results = await lintFile(file);
    expect(results.flatMap((r) => r.messages)).toHaveLength(0);

    const r = await decide({
      runners: [{ name: "require-provenance-output", fn: lintRunner(file) }],
    });

    expect(r.allow).toBe(true);
    expect(r.reason).toBe("all gates passed");
  });

  it("flags a raw local but not a wrapped one — the local-tracking behaviour users rely on", async () => {
    // Both return a LOCAL, so this pins the rule's local classification rather
    // than only its direct-return path.
    //
    // Be precise about what it does NOT prove. The rule stays silent on any
    // unclassifiable return by design (its zero-false-positive contract), so
    // `return frobnicate(x, r)` and a deleted provenance import both pass
    // identically. Silence therefore cannot distinguish "recognised as tagged"
    // from "could not classify" — and no black-box test can, because the
    // tracked-import path has NO observable effect on this rule's output:
    // `localClass` is set to "tagged" but the only read tests for "raw", and
    // the two classifications are mutually exclusive anyway. Verified by
    // mutation: disabling PRIMITIVE_SOURCE matching leaves every test green.
    // Tracked as its own defect (#212) rather than papered over here.
    const raw = writeSource(
      "local-raw.mjs",
      `export function f(x, r) { const t = x * r; return t; }`,
    );
    const tagged = writeSource(
      "local-tagged.mjs",
      `export function f(x, r) { const t = derive([x, r], (p, q) => p * q); return t; }`,
    );

    expect((await lintFile(raw)).flatMap((r) => r.messages).map((m) => m.ruleId))
      .toContain(RULE);
    expect((await lintFile(tagged)).flatMap((r) => r.messages)).toHaveLength(0);
  });
});
