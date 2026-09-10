// primitives/js/baseline.mjs — Principle 9: golden baseline + explain-the-drift.
//
// Pins a marked value WITH its trust state, diffs later runs against the pin,
// refuses silent drift, and requires a recorded explanation to accept a new
// state. Attribution is what separates this from snapshot testing: the
// envelope's lineage records each input's state at combination time, so a
// drift can say which input moved. See docs/adr/0015-baseline-library-first.md
// and SPEC §4 for the lineage shape. Mirror of primitives/python/baseline.py;
// parity is pinned by primitives/conformance/baseline-cases.json.
import { readFileSync, writeFileSync, renameSync, readdirSync, mkdirSync, existsSync, statSync, unlinkSync } from "node:fs";
import { join, resolve } from "node:path";
import { randomBytes } from "node:crypto";
import { PROVENANCE_VERSION } from "./provenance.mjs";
import { validateEnvelope } from "./audit.mjs";
import { metaOf, unwrap } from "./marked.mjs";

export const BASELINE_FORMAT = "v1";
export const KNOWN_BASELINE_FORMATS = new Set(["v1"]);
export const DEFAULT_DIR = ".plumb-line/baselines";
export const NAME_RE = /^[A-Za-z0-9._-]+$/;
export const STEP_FIELDS = ["source", "confidence", "confidenceScore", "derivedFromMock", "of"];
export const TOP_FIELDS = ["source", "confidence", "confidenceScore", "derivedFromMock"];
const RECORD_KEYS = ["baseline-format", "name", "provenanceVersion", "value", "meta", "history"];
const DATE_RE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

// ---------- canonical JSON ----------

export function canonicalize(x) {
  if (Array.isArray(x)) return x.map(canonicalize);
  if (x && typeof x === "object") {
    const out = {};
    for (const k of Object.keys(x).sort()) out[k] = canonicalize(x[k]);
    return out;
  }
  return x;
}

export function canonicalJson(x) {
  return JSON.stringify(canonicalize(x), null, 2) + "\n";
}

export function compactJson(x) {
  const s = JSON.stringify(canonicalize(x));
  return s === undefined ? "null" : s;
}

export function isJsonValue(x) {
  try {
    const s = JSON.stringify(x);
    if (s === undefined) return false;
    return deepEqual(JSON.parse(s), x);
  } catch {
    return false;
  }
}

export function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    return deepEqual(ka, kb) && ka.every((k) => deepEqual(a[k], b[k]));
  }
  return false;
}

// ---------- attribution ----------

function finding(path, before, after, text) {
  return { path, before: before === undefined ? null : before, after: after === undefined ? null : after, text };
}

const fieldText = (path, b, a) => `${path}: ${compactJson(b)} -> ${compactJson(a)}`;

/**
 * Compare a pinned record against a new wire-form envelope + value.
 * Returns findings in the fixed order: version, per-step fields, lineage
 * length, top-level fields not explained by a step finding, value.
 */
export function compare(record, wireMeta, value, runningVersion = PROVENANCE_VERSION) {
  const f = [];
  if (record.provenanceVersion !== runningVersion) {
    f.push(finding("provenanceVersion", record.provenanceVersion, runningVersion,
                   `pinned under wire v${record.provenanceVersion}, running v${runningVersion}`));
  }
  const pl = Array.isArray(record.meta?.lineage) ? record.meta.lineage : [];
  const nl = Array.isArray(wireMeta?.lineage) ? wireMeta.lineage : [];
  const touched = new Set();
  for (let i = 0; i < Math.min(pl.length, nl.length); i++) {
    for (const field of STEP_FIELDS) {
      const b = pl[i]?.[field], a = nl[i]?.[field];
      if (!deepEqual(b === undefined ? null : b, a === undefined ? null : a)) {
        const path = `meta.lineage[${i}].${field}`;
        f.push(finding(path, b, a, fieldText(path, b, a)));
        touched.add(field);
      }
    }
  }
  if (pl.length !== nl.length) {
    const grew = nl.length > pl.length;
    const n = Math.abs(nl.length - pl.length);
    const k = Math.min(pl.length, nl.length);
    f.push(finding("meta.lineage.length", pl.length, nl.length,
                   grew ? `lineage grew by ${n} (first new step: meta.lineage[${k}])`
                        : `lineage shrank by ${n} (first missing step: meta.lineage[${k}])`));
    touched.add("length");
  }
  for (const field of TOP_FIELDS) {
    const b = record.meta?.[field], a = wireMeta?.[field];
    if (!touched.has(field) && !deepEqual(b === undefined ? null : b, a === undefined ? null : a)) {
      const path = `meta.${field}`;
      f.push(finding(path, b, a, fieldText(path, b, a)));
    }
  }
  if (!deepEqual(record.value, value)) {
    const attributed = f.some((x) => x.path.startsWith("meta."));
    f.push(finding("value", record.value, value,
                   attributed ? "value moved; attributed to the findings above"
                              : "value moved with no input change"));
  }
  return f;
}

export function summarize(findings) {
  return findings.length ? findings.map((x) => x.text).join("; ") : "none";
}

// ---------- record ----------

export function toRecord(name, marked, history) {
  const wire = { ...metaOf(marked) };
  const provenanceVersion = wire.provenanceVersion;
  delete wire.provenanceVersion;
  return {
    "baseline-format": BASELINE_FORMAT,
    name,
    provenanceVersion,
    value: unwrap(marked),
    meta: wire,
    history,
  };
}

/** P7 validator for a parsed record. [] when valid; never throws. */
export function validateBaseline(record) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return ["not a baseline record"];
  const issues = [];
  for (const k of RECORD_KEYS) if (!(k in record)) issues.push(`missing required key: ${k}`);
  if ("baseline-format" in record && !KNOWN_BASELINE_FORMATS.has(record["baseline-format"])) {
    issues.push(`unknown baseline-format ${JSON.stringify(record["baseline-format"])} (this library models ${[...KNOWN_BASELINE_FORMATS].join(", ")})`);
  }
  if ("name" in record && !(typeof record.name === "string" && NAME_RE.test(record.name))) {
    issues.push(`name must match ${NAME_RE}`);
  }
  if ("provenanceVersion" in record && !Number.isInteger(record.provenanceVersion)) {
    issues.push("provenanceVersion must be an integer");
  }
  if ("meta" in record) {
    // Only a plain object can carry provenanceVersion; anything else (null,
    // an array, a string, a number) reaches validateEnvelope unchanged, so it
    // reports "not an envelope object" / "missing meta" exactly as Python
    // does instead of being spread into a bag of index keys.
    const m = record.meta;
    const target = m && typeof m === "object" && !Array.isArray(m)
      ? { ...m, provenanceVersion: record.provenanceVersion }
      : m;
    for (const i of validateEnvelope(target)) issues.push(`meta: ${i}`);
  }
  if ("history" in record) {
    if (!Array.isArray(record.history) || record.history.length === 0) {
      issues.push("history must be a non-empty array");
    } else {
      record.history.forEach((h, i) => {
        if (!h || typeof h !== "object") { issues.push(`history[${i}] must be an object`); return; }
        if (typeof h.date !== "string" || !DATE_RE.test(h.date)) issues.push(`history[${i}].date must be YYYY-MM-DD`);
        if (typeof h.because !== "string" || !h.because.trim()) issues.push(`history[${i}].because must be a non-empty string`);
        if (typeof h.change !== "string") issues.push(`history[${i}].change must be a string`);
      });
    }
  }
  return issues;
}

// ---------- file store ----------

/** True only for an existing directory. Twin of Python's os.path.isdir: a
 * regular file (or a missing path) is not a baselines directory, so callers
 * degrade to "nothing here" instead of crashing with ENOTDIR. */
export function isDir(p) {
  return statSync(p, { throwIfNoEntry: false })?.isDirectory() ?? false;
}

const pathFor = (dir, name) => join(resolve(dir), `${name}.json`);

function readRecord(dir, name) {
  const path = pathFor(dir, name);
  if (!existsSync(path)) return { status: "missing", path };
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    return { status: "invalid", path, issues: [`cannot parse: ${e.message}`] };
  }
  const issues = validateBaseline(parsed);
  if (issues.length) return { status: "invalid", path, issues };
  if (parsed.name !== name) return { status: "invalid", path, issues: [`name ${JSON.stringify(parsed.name)} does not match the filename`] };
  return { status: "ok", path, record: parsed };
}

function requireName(name) {
  if (typeof name !== "string" || !NAME_RE.test(name)) {
    throw new Error(`baseline name must match ${NAME_RE}, got ${JSON.stringify(name)}`);
  }
}

export function check(name, marked, { dir = DEFAULT_DIR } = {}) {
  requireName(name);
  const envelopeIssues = validateEnvelope(metaOf(marked));
  if (envelopeIssues.length) {
    return { status: "invalid-envelope", name, dir: resolve(dir), findings: [], summary: "none", issues: envelopeIssues };
  }
  const read = readRecord(dir, name);
  if (read.status !== "ok") {
    return { status: read.status, name, dir: resolve(dir), path: read.path, findings: [], summary: "none", issues: read.issues || [] };
  }
  const findings = compare(read.record, metaOf(marked), unwrap(marked), PROVENANCE_VERSION);
  return { status: findings.length ? "drift" : "match", name, dir: resolve(dir), path: read.path,
           findings, summary: summarize(findings) };
}

export function reportText(report) {
  const head = `baseline ${report.name} (${report.dir}): ${report.status}`;
  switch (report.status) {
    case "match": return head;
    case "drift": return [head, ...report.findings.map((f) => `  ${f.text}`),
      `  accept with: update(${JSON.stringify(report.name)}, <marked>, { because: "<why the new state is correct>", dir: ${JSON.stringify(report.dir)} })`].join("\n");
    case "missing": return [head,
      `  no baseline file at ${report.path}`,
      `  record one with: update(${JSON.stringify(report.name)}, <marked>, { because: "<why this state is correct>", dir: ${JSON.stringify(report.dir)} })`].join("\n");
    case "invalid": return [head, `  ${report.path} is not a valid baseline record:`, ...report.issues.map((i) => `    ${i}`)].join("\n");
    case "invalid-envelope": return [head, "  the marked value's envelope is not valid:", ...report.issues.map((i) => `    ${i}`)].join("\n");
    default: return head;
  }
}

export function assertBaseline(name, marked, opts = {}) {
  const report = check(name, marked, opts);
  if (report.status !== "match") throw new Error(reportText(report));
}

export function update(name, marked, { because, dir = DEFAULT_DIR, date } = {}) {
  requireName(name);
  if (typeof because !== "string" || !because.trim()) {
    throw new Error("update requires `because`: a non-empty explanation of why the new state is correct");
  }
  const envelopeIssues = validateEnvelope(metaOf(marked));
  if (envelopeIssues.length) throw new Error(`cannot pin an invalid envelope: ${envelopeIssues.join("; ")}`);
  const value = unwrap(marked);
  if (!isJsonValue(value)) throw new Error("cannot pin a value that is not JSON-serialisable");
  const read = readRecord(dir, name);
  if (read.status === "invalid") throw new Error(`refusing to overwrite an invalid baseline at ${read.path}: ${read.issues.join("; ")}`);
  const today = date || new Date().toISOString().slice(0, 10);
  let history, change;
  if (read.status === "missing") {
    history = []; change = "initial";
  } else {
    history = read.record.history.slice();
    change = summarize(compare(read.record, metaOf(marked), value, PROVENANCE_VERSION));
  }
  history.push({ date: today, because: because.trim(), change });
  const record = toRecord(name, marked, history);
  const absDir = resolve(dir);
  mkdirSync(absDir, { recursive: true });
  const tmp = join(absDir, `.${name}.${randomBytes(4).toString("hex")}.tmp`);
  try {
    writeFileSync(tmp, canonicalJson(record), "utf8");
    renameSync(tmp, pathFor(dir, name));
  } catch (e) {
    try { unlinkSync(tmp); } catch { /* nothing to clean */ }
    throw e;
  }
  return record;
}

export function list({ dir = DEFAULT_DIR } = {}) {
  const absDir = resolve(dir);
  if (!isDir(absDir)) return [];
  return readdirSync(absDir).filter((f) => f.endsWith(".json") && !f.startsWith("."))
    .map((f) => f.slice(0, -".json".length)).sort();
}

export function show(name, { dir = DEFAULT_DIR } = {}) {
  requireName(name);
  const read = readRecord(dir, name);
  if (read.status === "missing") throw new Error(`no baseline named ${name} in ${resolve(dir)}`);
  if (read.status === "invalid") throw new Error(`${read.path} is not a valid baseline record: ${read.issues.join("; ")}`);
  return read.record;
}
