"use strict";
// ESLint plugin wrapper for the provenance-bypass rule, so a host project can
// register it: `plugins: { "plumb-line": require(".../provenance-lint") }`.
const rule = require("./no-provenance-bypass.cjs");

module.exports = {
  meta: { name: "eslint-plugin-plumb-line-provenance", version: "0.2.0" },
  rules: { "no-provenance-bypass": rule },
};
