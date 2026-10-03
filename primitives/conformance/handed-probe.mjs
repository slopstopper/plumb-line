#!/usr/bin/env node
// handed-probe.mjs — the JS half of the handed-envelope differential probe
// (#525, #594). Not run by hand: primitives/conformance/handed_probe.py
// spawns it, so both twins read the same input text.
//
//   node primitives/conformance/handed-probe.mjs [ROOT] < texts.json
//
// stdin is a JSON array of JSON texts, each an array of `combine` inputs.
// Each text is parsed here by JSON.parse, as a JS caller would read it, so a
// value the two languages' JSON parsers read differently (-0, 1.0, an integer
// beyond double range) reaches this twin as JS reads it. stdout is one record
// per text: what this twin's combine, audit and egress guard make of it, with
// a number JSON cannot write tagged (tagNumbers). ROOT (default: this checkout) is the tree whose
// primitives/js is probed, so an older tree can be probed as well.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = process.argv[2] ?? fileURLToPath(new URL("../..", import.meta.url));
const P = await import(pathToFileURL(resolve(root, "primitives/js/index.mjs")).href);

function record(text) {
  const inputs = JSON.parse(text);
  let out;
  try {
    out = P.combineProvenance(...inputs);
  } catch (e) {
    // A throw is recorded as one, without its message: the two languages'
    // error texts are not part of the contract, whether each throws is.
    return { combine: { raises: true }, detail: String(e?.message) };
  }
  const r = { combine: out };
  try {
    r.audit = P.auditMeta(out);
  } catch (e) {
    r.audit = { raises: true };
    r.detail = String(e?.message);
  }
  try {
    P.guard({ value: 1, ...out });
    r.guard = { pass: true };
  } catch (e) {
    r.guard = P.ProvenanceRefused && e instanceof P.ProvenanceRefused
      ? { refused: e.reasons }
      : { raises: true };
    if (!r.guard.refused) r.detail = String(e?.message);
  }
  return r;
}

// A number JSON cannot write is tagged, as the Python half's tag_numbers
// tags it: JSON.stringify would write Infinity and NaN as null and -0 as 0,
// and a genuine null or 0 would then hide a difference.
function tagNumbers(_key, v) {
  if (typeof v !== "number") return v;
  if (Object.is(v, -0)) return { $number: "-0" };
  return Number.isFinite(v) ? v : { $number: String(v) };
}

const texts = JSON.parse(readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(texts.map(record), tagNumbers));
