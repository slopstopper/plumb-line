/**
 * Integration test: prove the SHIPPED eslint-provenance template actually loads
 * and enforces, once its placeholders are filled the way bootstrap fills them.
 *
 * This test exists because the template did NOT load. It required
 * "./provenance-lint", and Node's directory-index resolution tries
 * index.js/.json/.node but not index.cjs — so the bootstrap-installable config
 * threw MODULE_NOT_FOUND for every user who copied it, for the pre-existing rule
 * as well as the new one. No test loaded the template, so nothing caught it
 * (found while wiring #164; the boundary template had an equivalent test, this
 * one did not).
 *
 * What is pinned here: the template's placeholder contract, that it resolves the
 * plugin, and that BOTH rules fire through it on real files — each inside its
 * own declared surface and not outside. The bypass case (#246) is the one that
 * was missing: the rule whose breakage motivated this file was proven to be
 * REGISTERED but never proven to fire through the shipped config.
 */

import { describe, it, expect, afterAll } from "vitest";
import { ESLint } from "eslint";
import { mkdtempSync, writeFileSync, rmSync, readFileSync, mkdirSync, cpSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
// __tests__ → hooks → js (= adapters/js/)
const ADAPTER_DIR = path.resolve(fileURLToPath(import.meta.url), "../../../");
const TEMPLATE_PATH = path.join(ADAPTER_DIR, "eslint-provenance.template.cjs");

const BYPASS = "plumb-line/no-provenance-bypass";
const OUTPUT = "plumb-line/require-provenance-output";

const workdir = mkdtempSync(path.join(tmpdir(), "plumb-tpl-"));
afterAll(() => rmSync(workdir, { recursive: true, force: true }));

/**
 * Do what bootstrap does: copy the plugin next to the config, fill the two
 * placeholders, write the result, and require it. Deliberately exercises the
 * template's own require() path rather than importing the plugin directly —
 * that resolution is the thing that was broken.
 */
function installTemplate(globs, outputGlobs) {
  cpSync(
    path.join(ADAPTER_DIR, "provenance-lint"),
    path.join(workdir, "provenance-lint"),
    { recursive: true },
  );
  // Target the `files:` assignments specifically. The placeholders are also
  // named in the template's comments, so a naive first-occurrence replace fills
  // the prose and leaves the code undefined — which is exactly what happened
  // when this test was first written. Bootstrap must be equally precise.
  const src = readFileSync(TEMPLATE_PATH, "utf8")
    .replace("files: __GLOBS__", `files: ${JSON.stringify(globs)}`)
    .replace("files: __OUTPUT_GLOBS__", `files: ${JSON.stringify(outputGlobs)}`);
  const configPath = path.join(workdir, "eslint.config.cjs");
  writeFileSync(configPath, src);
  // Node caches require()d modules by path. Every earlier caller passed the
  // same globs, so the cache silently serving the FIRST install never showed;
  // the first call with different globs got the old config and failed for
  // the wrong reason. Evict before requiring so each install is the one
  // asked for.
  delete require.cache[require.resolve(configPath)];
  return require(configPath);
}

function writeFile(rel, body) {
  const file = path.join(workdir, rel);
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, body);
  return file;
}

async function lint(config, file) {
  const eslint = new ESLint({
    cwd: workdir,
    overrideConfigFile: true,
    overrideConfig: config.map((block) => ({
      ...block,
      languageOptions: { ecmaVersion: 2022, sourceType: "module" },
    })),
  });
  const results = await eslint.lintFiles([file]);
  return results.flatMap((r) => r.messages);
}

describe("eslint-provenance.template.cjs (as bootstrap installs it)", () => {
  it("carries both placeholders — the contract bootstrap fills", () => {
    const src = readFileSync(TEMPLATE_PATH, "utf8");
    expect(src).toContain("__GLOBS__");
    expect(src).toContain("__OUTPUT_GLOBS__");
  });

  it("resolves the plugin and registers both rules", () => {
    const config = installTemplate(["src/**/*.mjs"], ["src/pricing/**/*.mjs"]);
    expect(config).toHaveLength(2);
    expect(Object.keys(config[0].rules)).toEqual([BYPASS]);
    expect(Object.keys(config[1].rules)).toEqual([OUTPUT]);
    // Plugin object actually resolved, not undefined.
    expect(config[0].plugins["plumb-line"].rules).toHaveProperty(
      "no-provenance-bypass",
    );
  });

  it("the output rule fires inside the declared surface", async () => {
    const config = installTemplate(["src/**/*.mjs"], ["src/pricing/**/*.mjs"]);
    const file = writeFile(
      "src/pricing/rate.mjs",
      `import { mark, derive } from "plumb-line-provenance";\n` +
        `export function f(x, r) { return x * r; }\n`,
    );
    const messages = await lint(config, file);
    expect(messages.map((m) => m.ruleId)).toContain(OUTPUT);
  });

  it("declined path: the __OUTPUT_GLOBS__ block removes cleanly, bypass survives (#214)", () => {
    // Step 4c's decline instruction followed literally: delete the second
    // config object, leading "Output-tag enforcement" comment through its
    // closing brace. The result must load with the bypass rule as the sole
    // entry — the class of failure pinned against is the 4b-declined-path
    // ReferenceError (#214 finding 3), where a surviving placeholder took
    // the whole config (bypass rule included) down with it.
    cpSync(
      path.join(ADAPTER_DIR, "provenance-lint"),
      path.join(workdir, "provenance-lint"),
      { recursive: true },
    );
    const filled = readFileSync(TEMPLATE_PATH, "utf8").replace(
      "files: __GLOBS__",
      `files: ${JSON.stringify(["src/**/*.mjs"])}`,
    );
    const start = filled.indexOf("  // Output-tag enforcement");
    expect(start).toBeGreaterThan(-1);
    // "through THAT object's closing },": the first block-closing brace at or
    // after the marker — never lastIndexOf, which would silently swallow any
    // block appended after the output block (#308 review).
    const end = filled.indexOf("\n  },", start);
    expect(end).toBeGreaterThan(start);
    const declined = filled.slice(0, start) + filled.slice(end + "\n  },\n".length);
    // The bypass block above the removal must survive verbatim.
    expect(declined).toContain('files: ["src/**/*.mjs"]');
    expect(declined).not.toContain("__OUTPUT_GLOBS__");
    const configPath = path.join(workdir, "eslint.config.declined.cjs");
    writeFileSync(configPath, declined);
    const config = require(configPath);
    expect(config).toHaveLength(1);
    expect(Object.keys(config[0].rules)).toEqual([BYPASS]);
  });

  it("the bypass rule fires inside __GLOBS__ (#246)", async () => {
    // PB1: a clean source asserted on an explicitly mock-tainted value — the
    // canonical laundering pattern (SPEC §5). Linted through the INSTALLED
    // template, not the plugin directly: the point is that the shipped config
    // carries the rule all the way to a message on a real file.
    const config = installTemplate(["src/**/*.mjs"], ["src/pricing/**/*.mjs"]);
    const file = writeFile(
      "src/data/load.mjs",
      `import { mark } from "plumb-line-provenance";\n` +
        `export const m = mark(1, { source: "real", derivedFromMock: true });\n`,
    );
    const messages = await lint(config, file);
    const bypass = messages.filter((m) => m.ruleId === BYPASS);
    expect(bypass).toHaveLength(1);
    expect(bypass[0].message).toMatch(/^PB1 /);
  });

  it("the bypass rule is silent OUTSIDE __GLOBS__", async () => {
    // Same laundering in a file the bypass globs do NOT cover but the output
    // globs DO — so the file is genuinely linted (a file no block covers
    // yields only ESLint's file-ignored warning, and a not-toContain on that
    // passes vacuously, on a parse error too). Here the only messages that
    // can appear come from the output rule, and none may come from the
    // bypass rule: that is the scoping claim.
    const config = installTemplate(["src/data/**/*.mjs"], ["src/pricing/**/*.mjs"]);
    const file = writeFile(
      "src/pricing/rate.mjs",
      `import { mark } from "plumb-line-provenance";\n` +
        `export const m = mark(1, { source: "real", derivedFromMock: true });\n` +
        `export function f(x, r) { return x * r; }\n`,
    );
    const messages = await lint(config, file);
    const ruleIds = messages.map((m) => m.ruleId);
    // The raw return proves the file was linted (the output rule fired)...
    expect(ruleIds).toContain(OUTPUT);
    // ...and the laundering on the line above drew nothing from the bypass
    // rule, because this file is outside the bypass globs.
    expect(ruleIds).not.toContain(BYPASS);
    expect(messages.filter((m) => m.fatal)).toHaveLength(0);
  });

  it("the output rule is silent OUTSIDE the declared surface", async () => {
    // The whole point of ADR-0011's declared surface: same untagged code, but
    // outside the boundary the rule does not exist.
    const config = installTemplate(["src/**/*.mjs"], ["src/pricing/**/*.mjs"]);
    const file = writeFile(
      "src/util/slug.mjs",
      `import { mark, derive } from "plumb-line-provenance";\n` +
        `export function f(x, r) { return x * r; }\n`,
    );
    const messages = await lint(config, file);
    expect(messages.map((m) => m.ruleId)).not.toContain(OUTPUT);
  });
});
