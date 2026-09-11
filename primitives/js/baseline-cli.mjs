#!/usr/bin/env node
// baseline-cli.mjs — inspect baseline records on disk: list, show, validate.
// Deliberately cannot check or update: only running code has the new
// envelope, so those live in the library (docs/adr/0015). Twin:
// python3 -m plumb_line_provenance.baseline. Excluded from the plugin bundle
// (tooling, not runtime).
import { readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { list, show, validateBaseline, compactJson, isDir, DEFAULT_DIR } from "./baseline.mjs";

const USAGE = "usage: baseline <list|show <name>|validate> [--dir D]";

function parse(argv) {
  const args = [...argv];
  let dir = DEFAULT_DIR;
  const i = args.indexOf("--dir");
  if (i >= 0) {
    // `--dir` with nothing after it (or another flag) is a mistake, not a
    // request for the default directory: fail loudly rather than inspect a
    // directory the caller did not name. Twin of the same guard in baseline.py.
    const v = args[i + 1];
    if (v === undefined || v.startsWith("-")) return { usageError: true };
    dir = v;
    args.splice(i, 2);
  }
  return { cmd: args[0], name: args[1], dir };
}

export function main(argv) {
  const { cmd, name, dir, usageError } = parse(argv);
  if (usageError) { console.error(USAGE); return 2; }
  const absDir = resolve(dir || DEFAULT_DIR);
  if (cmd === "list") {
    if (!isDir(absDir)) { console.log(`no baselines directory at ${absDir}`); return 0; }
    const names = list({ dir: absDir });
    for (const n of names) console.log(n);
    console.log(`${names.length} baseline(s) in ${absDir}`);
    return 0;
  }
  if (cmd === "show") {
    if (!name) { console.error("usage: baseline show <name> [--dir D]"); return 2; }
    let rec;
    try { rec = show(name, { dir: absDir }); } catch (e) { console.error(e.message); return 1; }
    console.log(`${rec.name}  (baseline-format ${rec["baseline-format"]}, wire v${rec.provenanceVersion})`);
    console.log(`value: ${compactJson(rec.value)}`);
    for (const k of ["source", "confidence", "confidenceScore", "derivedFromMock", "weakestSource"]) {
      if (k in rec.meta) console.log(`${k}: ${JSON.stringify(rec.meta[k])}`);
    }
    console.log(`lineage: ${rec.meta.lineage.length} step(s)`);
    rec.meta.lineage.forEach((s, i) => console.log(`  [${i}] ${s.source}/${s.confidence}${s.derivedFromMock ? " tainted" : ""}${"confidenceScore" in s ? ` score ${s.confidenceScore}` : ""}`));
    console.log("history:");
    for (const h of rec.history) console.log(`  ${h.date}  ${h.change}  ${h.because}`);
    return 0;
  }
  if (cmd === "validate") {
    if (!isDir(absDir)) { console.log(`no baselines directory at ${absDir}; 0 files validated`); return 0; }
    const files = readdirSync(absDir).filter((f) => f.endsWith(".json") && !f.startsWith(".")).sort();
    let bad = 0;
    for (const f of files) {
      let issues, rec;
      try {
        rec = JSON.parse(readFileSync(join(absDir, f), "utf8"));
        issues = validateBaseline(rec);
      } catch (e) { issues = [`cannot parse: ${e.message}`]; }
      // The library reads by name, so a record filed under the wrong filename
      // is unreachable — a defect the validator alone cannot see, since it is
      // handed the record without its path.
      if (!issues.length && rec.name !== f.slice(0, -".json".length)) {
        issues = [`name ${JSON.stringify(rec.name)} does not match the filename`];
      }
      if (issues.length) { bad++; console.log(`✗ ${f}`); for (const i of issues) console.log(`    ${i}`); }
      else console.log(`✓ ${f}`);
    }
    console.log(bad ? `${bad} of ${files.length} invalid` : `${files.length} file(s) valid`);
    return bad ? 1 : 0;
  }
  console.error(USAGE);
  return 2;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main(process.argv.slice(2)));
}
