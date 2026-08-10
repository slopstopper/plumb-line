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
 * plugin, and that BOTH rules actually fire through it on real files.
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
