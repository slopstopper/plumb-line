#!/usr/bin/env node
// check-bundle-sync.mjs — verify the plugin-bundled primitive copy is
// byte-identical to its primitives/ source (the single source of truth), AND
// that the bundled set accounts for the primitive's whole published surface.
//
//   node scripts/check-bundle-sync.mjs
//
// The bundle at .claude-plugin/bundled/primitives/{js,python} lets a
// plugin-only user adopt the runtime with no npm/pip step. It must never
// silently drift from primitives/ — this script is the drift gate that CI
// runs on every push/PR. Exits 0 when every check passes; exits 1 and prints
// what is wrong otherwise.
//
// Three checks (#157 added the last two):
//   1. Byte equality of every bundled file with its source.
//   2. Surface accounting: every module the primitive PUBLISHES (JS: the
//      `files` list in package.json; Python: every top-level .py, since
//      pyproject packages the flat directory) is either bundled below or
//      excluded below WITH A RECORDED REASON. A new standalone module that is
//      neither fails here instead of being silently un-bundled — which was the
//      footgun: the pairs were hand-enumerated and nothing compared them to
//      what the package actually ships.
//   3. No orphans: nothing sits under the bundled tree that is not in the
//      bundled set (a stale file left behind by a rename would otherwise ship
//      to plugin users unverified).
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const at = (p) => join(root, p);

// The ONE manifest: which published modules are vendored, and which are not
// and why. The (source, bundled) pairs are derived from this, never listed by
// hand. To bundle a new module: add its basename to `bundled`. To keep one
// out: add it to `excluded` with the reason a plugin-only user would want.
const BUNDLE = {
  js: {
    sourceDir: "primitives/js",
    bundledDir: ".claude-plugin/bundled/primitives/js",
    bundled: ["provenance.mjs", "audit.mjs", "marked.mjs", "index.mjs"],
    excluded: {
      "http.mjs": "the ./http subpath adapter needs native fetch and the Age-header policy; the bundle is the dependency-free dual-import-shim core",
    },
    // What the package publishes: package.json `files`, minus docs.
    published: () => {
      const pkg = JSON.parse(readFileSync(at("primitives/js/package.json"), "utf8"));
      return (pkg.files || []).filter((f) => f.endsWith(".mjs"));
    },
  },
  python: {
    sourceDir: "primitives/python",
    bundledDir: ".claude-plugin/bundled/primitives/python",
    bundled: ["provenance.py", "audit.py", "marked.py", "__init__.py"],
    excluded: {
      "http.py": "optional-dependency adapter (requests/httpx extras); the bundle is the dependency-free core",
      "arrays.py": "optional-dependency adapter (numpy extra); the bundle is the dependency-free core",
      "frames.py": "optional-dependency adapter (pandas extra); the bundle is the dependency-free core",
    },
    // pyproject packages the flat directory (package-dir = "."), so every
    // top-level module is published.
    published: () =>
      readdirSync(at("primitives/python")).filter((f) => f.endsWith(".py")).sort(),
  },
};

const problems = [];

for (const [lang, spec] of Object.entries(BUNDLE)) {
  // 2. Surface accounting.
  const published = new Set(spec.published());
  const accounted = new Set([...spec.bundled, ...Object.keys(spec.excluded)]);
  for (const f of published) {
    if (!accounted.has(f)) {
      problems.push(`${lang}: ${f} is published by ${spec.sourceDir} but neither bundled nor excluded — add it to BUNDLE.${lang}.bundled, or to .excluded with a reason`);
    }
  }
  for (const f of accounted) {
    if (!published.has(f)) {
      problems.push(`${lang}: ${f} is listed in BUNDLE.${lang} but ${spec.sourceDir} does not publish it (renamed or removed?)`);
    }
  }

  // 1. Byte equality, over pairs DERIVED from the manifest.
  for (const f of spec.bundled) {
    const source = `${spec.sourceDir}/${f}`;
    const bundled = `${spec.bundledDir}/${f}`;
    if (!existsSync(at(source))) {
      problems.push(`${source}: source file missing (cannot verify bundle)`);
      continue;
    }
    if (!existsSync(at(bundled))) {
      problems.push(`${bundled}: bundle missing`);
      continue;
    }
    if (!readFileSync(at(source)).equals(readFileSync(at(bundled)))) {
      problems.push(`${bundled}: drifted from ${source}`);
    }
  }

  // 3. Orphans. Byte-compiled caches are untracked build artefacts (running
  // the bundle-conformance suite writes __pycache__ into the bundled tree);
  // they never ship and are not orphans.
  if (existsSync(at(spec.bundledDir))) {
    for (const f of readdirSync(at(spec.bundledDir))) {
      if (f === "__pycache__" || f.endsWith(".pyc")) continue;
      if (!spec.bundled.includes(f)) {
        problems.push(`${spec.bundledDir}/${f}: not in BUNDLE.${lang}.bundled — an orphan that would ship to plugin users unverified`);
      }
    }
  }
}

if (problems.length) {
  console.error("✗ bundle check failed:");
  for (const p of problems) console.error(`    ${p}`);
  console.error("  Byte drift: re-copy the file from primitives/ into .claude-plugin/bundled/primitives/.");
  console.error("  Surface: edit the BUNDLE manifest in scripts/check-bundle-sync.mjs.");
  process.exit(1);
}

const checked = Object.values(BUNDLE).reduce((n, s) => n + s.bundled.length, 0);
const excluded = Object.values(BUNDLE).reduce((n, s) => n + Object.keys(s.excluded).length, 0);
// Stated as a breakdown, not a ratio: by this point every published module
// is accounted for (an unaccounted one exited above), so an "N/N" would be
// the same count twice dressed as a measurement.
const surface = Object.entries(BUNDLE)
  .map(([lang, s]) =>
    `${lang} ${s.published().length} (${s.bundled.length} bundled + ${Object.keys(s.excluded).length} excluded)`)
  .join(", ");
console.log(`✓ bundle in sync with primitives/ (${checked} files byte-checked; ${excluded} excluded by recorded reason; published surface accounted: ${surface})`);
