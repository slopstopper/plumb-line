#!/usr/bin/env node
// bump-version.mjs — set the package + plugin versions in lockstep.
//
//   node scripts/bump-version.mjs <version>     e.g. node scripts/bump-version.mjs 0.3.0
//
// Updates the three version manifests that must always agree:
//   - primitives/js/package.json        (npm package)
//   - primitives/python/pyproject.toml  (PyPI package)
//   - .claude-plugin/plugin.json        (Claude Code plugin — its version is what
//                                        triggers an update for already-installed users)
//
// NOT touched: PROVENANCE_VERSION (the envelope schema/wire version) — that only
// changes on a breaking change to the metadata format, independent of releases.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const version = process.argv[2];

if (!version || !/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error("usage: node scripts/bump-version.mjs <version>   (e.g. 0.3.0)");
  process.exit(1);
}

const targets = [
  { file: "primitives/js/package.json", re: /("version":\s*")[^"]*(")/, label: "npm" },
  { file: ".claude-plugin/plugin.json", re: /("version":\s*")[^"]*(")/, label: "plugin" },
  { file: "primitives/python/pyproject.toml", re: /^(version\s*=\s*")[^"]*(")/m, label: "PyPI" },
];

let ok = true;
for (const t of targets) {
  const path = join(root, t.file);
  const src = readFileSync(path, "utf8");
  if (!t.re.test(src)) {
    console.error(`✗ ${t.file}: version field not found`);
    ok = false;
    continue;
  }
  writeFileSync(path, src.replace(t.re, `$1${version}$2`));
  console.log(`✓ ${t.label.padEnd(7)} ${t.file} → ${version}`);
}

if (!ok) process.exit(1);

promoteChangelog(version);

console.log(`\nAll manifests set to ${version}.`);
console.log("Next: commit as a release PR, merge, then `git tag v" + version + " && git push origin v" + version + "`.");

// Promote CHANGELOG `## [Unreleased]` to `## [<version>] — <date>` and leave a
// fresh empty Unreleased, so a release can't be tagged without notes. Best-effort:
// if the CHANGELOG doesn't match the expected shape, warn and leave it untouched
// (the release workflow's CHANGELOG guard is the backstop).
function promoteChangelog(v) {
  const path = join(root, "CHANGELOG.md");
  let src;
  try {
    src = readFileSync(path, "utf8");
  } catch {
    console.warn("• CHANGELOG.md not found — skipping changelog promotion");
    return;
  }

  if (src.includes(`## [${v}]`)) {
    console.log(`• CHANGELOG already has a [${v}] section — leaving it as-is`);
    return;
  }

  // Previous version + repo compare URL come from the [Unreleased] link line.
  const linkRe = /^\[Unreleased\]:\s*(https?:\/\/\S+\/compare\/)v(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\.\.\.HEAD\s*$/m;
  const lm = src.match(linkRe);
  if (!lm) {
    console.warn("• couldn't find the [Unreleased] compare link — skipping changelog promotion");
    return;
  }
  const [, compareBase, prev] = lm;

  // The Unreleased section body sits between its header and the next `## [`.
  const secRe = /## \[Unreleased\]\s*\n([\s\S]*?)\n(## \[)/;
  const sm = src.match(secRe);
  if (!sm) {
    console.warn("• couldn't find the [Unreleased] section — skipping changelog promotion");
    return;
  }
  const body = sm[1].trim();
  if (!body || /^_Nothing yet\._?$/i.test(body)) {
    console.warn(`• [Unreleased] has no notes — not promoting (add notes before releasing ${v})`);
    return;
  }

  const date = new Date().toISOString().slice(0, 10);
  src = src.replace(
    secRe,
    `## [Unreleased]\n\n_Nothing yet._\n\n## [${v}] — ${date}\n\n${body}\n\n${sm[2]}`,
  );
  src = src.replace(
    linkRe,
    `[Unreleased]: ${compareBase}v${v}...HEAD\n[${v}]: ${compareBase}v${prev}...v${v}`,
  );

  writeFileSync(path, src);
  console.log(`✓ CHANGELOG  [Unreleased] → [${v}] — ${date} (previous v${prev})`);
}
