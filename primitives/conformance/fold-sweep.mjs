#!/usr/bin/env node
// fold-sweep.mjs — the JS half of the case-fold sweep (#625, #642). Not run
// by hand: primitives/conformance/fold_sweep.py spawns it, and compares what
// it prints with what the running Python makes of the same code points.
//
//   node primitives/conformance/fold-sweep.mjs > node.json
//
// For every code point except the surrogates, it records what this Node's
// Unicode tables say, as the hooks read them (adapters/js/hooks/branch-guard.mjs):
// - `known`: the code points that are not `Cn` (UNKNOWN there), as ranges;
// - `folds`: each known code point whose fold is not itself, with that fold
//   (`fold` there: NFC, then upper, then lower case);
// - `marks`: each known code point that is its own NFD and has a canonical
//   combining class other than 0, found through NFD's canonical ordering,
//   since JS has no API for the class (see `reorders`);
// - `acute`: those of the marks that NFC moves or composes across in
//   "e" + mark + U+0301, PARITY.md's example: a class other than 0 and 230;
// - `composites`: each known primary composite, with its NFD (a code point
//   whose NFD differs from it and composes back to it under NFC).

const fold = (name) => String(name).normalize("NFC").toUpperCase().toLowerCase();
const UNKNOWN = /^\p{Cn}$/u;

// Whether a code point that is its own NFD has a canonical combining class
// other than 0. NFD's canonical ordering moves a mark of class k after a
// following mark of lower class, and never moves a class-0 code point.
// U+0334 has class 1 and U+0345 class 240, the lowest and highest classes
// above 0: "x" + c + U+0334 reorders when c's class is above 1, and
// "x" + U+0345 + c when it is from 1 to 239, so either reorders exactly when
// it is not 0. fold_sweep.py checks this rule against Python's own
// unicodedata.combining on every code point Python knows that is its own NFD.
const reorders = (c) =>
  ("x" + c + "\u0334").normalize("NFD") !== "x" + c + "\u0334"
  || ("x\u0345" + c).normalize("NFD") !== "x\u0345" + c;

// Whether c has a combining class other than 0 and 230, the marks PARITY.md's
// example reaches: in "e" + c + U+0301, NFC then moves U+0301 before c (a
// class above 230) or composes it with "e" across c (a class below). Found as
// `reorders` is, against U+0301's class 230: "x" + c + U+0301 reorders under
// NFD when c's class is above 230, and "x" + U+0301 + c when it is from 1 to
// 229.
const acuteMoves = (c) =>
  ("x" + c + "\u0301").normalize("NFD") !== "x" + c + "\u0301"
  || ("x\u0301" + c).normalize("NFD") !== "x\u0301" + c;

const known = [];
const folds = {};
const marks = [];
const acute = [];
const composites = {};
for (let cp = 0; cp <= 0x10ffff; cp++) {
  if (cp >= 0xd800 && cp <= 0xdfff) continue;
  const c = String.fromCodePoint(cp);
  if (UNKNOWN.test(c)) continue;
  const last = known[known.length - 1];
  if (last && last[1] === cp - 1) last[1] = cp;
  else known.push([cp, cp]);
  const f = fold(c);
  if (f !== c) folds[cp] = f;
  const d = c.normalize("NFD");
  if (d === c && reorders(c)) {
    marks.push(cp);
    if (acuteMoves(c)) acute.push(cp);
  }
  if (d !== c && d.normalize("NFC") === c) composites[cp] = d;
}

process.stdout.write(JSON.stringify({
  node: process.version,
  unicode: process.versions.unicode ?? null,
  known, folds, marks, acute, composites,
}));
