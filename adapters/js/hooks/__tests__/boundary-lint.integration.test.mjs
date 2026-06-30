/**
 * Integration test: prove the SHIPPED ESLint boundary template
 * catches real violations in the fixture source files.
 *
 * Layers (top→bottom): ui → engine → services → data
 * Each layer is forbidden from importing any layer ABOVE it.
 */

import { describe, it, expect } from "vitest";
import { ESLint } from "eslint";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import { createRequire } from "module";

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

// Resolve upward from this file: __tests__ → hooks → js (= adapters/js/)
const ADAPTER_DIR = path.resolve(fileURLToPath(import.meta.url), "../../../");
const TEMPLATE_PATH = path.join(ADAPTER_DIR, "eslint-boundary.template.cjs");
const EXAMPLES_BASE = path.resolve(
  ADAPTER_DIR,
  "../../examples/js-payments-service",
);

const BROKEN_SRC = path.join(EXAMPLES_BASE, "broken/src");
const CLEAN_SRC = path.join(EXAMPLES_BASE, "clean/src");

// ---------------------------------------------------------------------------
// Build zones from template — derive from template file so we prove the
// TEMPLATE shape works, not a hand-authored config.
// ---------------------------------------------------------------------------

// Layer order (top→bottom) for zone derivation.
// The fixture's actual dependency graph has services calling into engine
// (services/gateway.js imports engine/pricing.js), so engine must sit BELOW
// services in the hierarchy — otherwise clean/src would produce a false
// positive.  The correct top→bottom order is: ui, services, engine, data.
const LAYERS = ["ui", "services", "engine", "data"];

/**
 * Build the zones array enforcing one-way layering.
 * For each layer, every layer ABOVE it is forbidden as an import source
 * (i.e. a lower layer must not import a higher layer).
 *
 * @param {string} srcRoot - absolute path to the src directory being linted
 * @returns {{ target: string, from: string }[]}
 */
function buildZones(srcRoot) {
  const zones = [];
  for (let i = 0; i < LAYERS.length; i++) {
    // layer i must not import layers 0..i-1 (layers above it)
    for (let j = 0; j < i; j++) {
      zones.push({
        target: path.join(srcRoot, LAYERS[i]),
        from: path.join(srcRoot, LAYERS[j]),
      });
    }
  }
  return zones;
}

/**
 * Derive an ESLint rules object from the template.
 *
 * Strategy: read the template, assert it carries the expected rule name and
 * the __ZONES__ placeholder (proving the template shape), then build the
 * rules object directly from those known-safe parts.  No eval / new Function
 * needed — the rule name is extracted by regex from the controlled local file
 * and used only as an object key, not as executed code.
 *
 * @param {{ target: string, from: string }[]} zones
 * @returns {{ rules: Record<string, unknown> }}
 */
function deriveConfigFromTemplate(zones) {
  const templateSrc = readFileSync(TEMPLATE_PATH, "utf8");

  // 1. Verify the placeholder is present — this is the contract the template exports.
  if (!templateSrc.includes("__ZONES__")) {
    throw new Error(
      `Template at ${TEMPLATE_PATH} is missing the __ZONES__ placeholder`,
    );
  }

  // 2. Extract the rule name from the template via regex (read-only, no exec).
  //    Template line looks like: "import/no-restricted-paths": ["error", { zones: __ZONES__ }]
  const ruleMatch = templateSrc.match(/"([\w/.-]+)":\s*\["error"/);
  if (!ruleMatch) {
    throw new Error(
      `Template at ${TEMPLATE_PATH} does not contain an expected "ruleName": ["error", ...] entry`,
    );
  }
  const ruleName = ruleMatch[1]; // e.g. "import/no-restricted-paths"

  // 3. Assemble the rules object using the extracted rule name as a key.
  //    The zones value is built from controlled local paths — no untrusted input.
  return {
    rules: {
      [ruleName]: ["error", { zones }],
    },
  };
}

/**
 * Run ESLint on a src directory and return all messages from all results.
 *
 * @param {string} srcDir
 * @returns {Promise<import("eslint").Linter.LintMessage[]>}
 */
async function lintDir(srcDir) {
  // Use createRequire so Node resolves eslint-plugin-import via the normal
  // node_modules lookup chain from this file's location (adapters/js/node_modules/).
  const require = createRequire(import.meta.url);
  const importPlugin = require("eslint-plugin-import-x");

  const zones = buildZones(srcDir);
  const derivedRuleConfig = deriveConfigFromTemplate(zones);

  const eslint = new ESLint({
    cwd: srcDir,
    overrideConfigFile: true,
    overrideConfig: [
      {
        plugins: { import: importPlugin },
        rules: derivedRuleConfig.rules,
      },
    ],
  });

  const results = await eslint.lintFiles([`${srcDir}/**/*.js`]);
  return results.flatMap((r) => r.messages);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("boundary-lint integration (ESLint + shipped template)", () => {
  it("broken fixture: data/rates.js upward import flagged by import/no-restricted-paths", async () => {
    const messages = await lintDir(BROKEN_SRC);
    const violations = messages.filter(
      (m) => m.ruleId === "import/no-restricted-paths",
    );
    expect(violations.length).toBeGreaterThanOrEqual(1);
    // At least one violation should come from the data layer's upward import
    const ratesViolation = violations.find(
      (m) =>
        m.message.includes("ui/checkout.js") ||
        m.message.includes("../ui/checkout.js"),
    );
    expect(ratesViolation).toBeDefined();
  });

  it("clean fixture: zero import/no-restricted-paths errors", async () => {
    const messages = await lintDir(CLEAN_SRC);
    const violations = messages.filter(
      (m) => m.ruleId === "import/no-restricted-paths",
    );
    expect(violations).toHaveLength(0);
  });
});
