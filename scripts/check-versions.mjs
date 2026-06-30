#!/usr/bin/env node
// check-versions.mjs — verify the three release manifests report the same version.
//
//   node scripts/check-versions.mjs            # CI use: assert the 3 manifests agree
//   node scripts/check-versions.mjs v0.3.0     # release use: also assert they equal the tag
//
// The three manifests that must always agree:
//   - primitives/js/package.json        (npm package)
//   - .claude-plugin/plugin.json        (Claude Code plugin)
//   - primitives/python/pyproject.toml  (PyPI package)
//
// Exits 0 and prints the agreed version; exits 1 (with a clear message) on any
// disagreement, or — when an expected version is given — if the manifests do
// not equal it. This is the guard that makes a premature or mismatched tag
// unpublishable: the release workflow runs it with the pushed tag.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

const read = (file, re) => {
  const src = readFileSync(join(root, file), "utf8");
  const m = src.match(re);
  if (!m) {
    console.error(`✗ ${file}: version field not found`);
    process.exit(1);
  }
  return m[1];
};

const manifests = {
  npm: read("primitives/js/package.json", /"version":\s*"([^"]+)"/),
  plugin: read(".claude-plugin/plugin.json", /"version":\s*"([^"]+)"/),
  pypi: read("primitives/python/pyproject.toml", /^version\s*=\s*"([^"]+)"/m),
};

const distinct = [...new Set(Object.values(manifests))];
if (distinct.length !== 1) {
  console.error("✗ manifest versions disagree:");
  for (const [k, v] of Object.entries(manifests)) console.error(`    ${k.padEnd(7)} ${v}`);
  console.error("  Run `node scripts/bump-version.mjs <version>` to set them in lockstep.");
  process.exit(1);
}
const version = distinct[0];

const expected = (process.argv[2] || "").replace(/^v/, "");
if (expected && expected !== version) {
  console.error(`✗ manifests are at ${version} but the tag is v${expected}.`);
  console.error("  Tag the commit AFTER the version-bump PR is merged (tag must equal the manifests).");
  process.exit(1);
}

console.log(`✓ all three manifests at ${version}${expected ? " (matches tag)" : ""}`);
