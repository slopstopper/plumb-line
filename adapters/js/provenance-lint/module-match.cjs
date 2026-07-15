"use strict";
// Shared module-name matching for the provenance-lint rules. The INJECTED
// `modules` option matches on normalized basename (#138): basename after the
// last "/", a known extension stripped, and "_" folded to "-" so "myorg_data"
// and "myorg-data" are the same module. Built-in coverage (the PRIMITIVE_SOURCE
// regex in each rule) is separate and unaffected.
const EXT = /\.(mjs|cjs|js|py)$/;

function normalizeModuleName(spec) {
  const base = String(spec).split("/").pop().replace(EXT, "");
  return base.replace(/_/g, "-");
}

function matchesExtraModule(spec, normalizedExtras) {
  return normalizedExtras.has(normalizeModuleName(spec));
}

module.exports = { normalizeModuleName, matchesExtraModule };
