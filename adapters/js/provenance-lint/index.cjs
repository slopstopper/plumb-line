"use strict";
// ESLint plugin wrapper for the provenance-lint rules, so a host project can
// register them: `plugins: { "plumb-line": require(".../provenance-lint/index.cjs") }`.
// The path must reach index.cjs: Node's directory-index resolution does not try
// index.cjs, so a bare directory require throws MODULE_NOT_FOUND.
const noBypass = require("./no-provenance-bypass.cjs");
const requireOutput = require("./require-provenance-output.cjs");

module.exports = {
  meta: { name: "eslint-plugin-plumb-line-provenance", version: "0.3.0" },
  rules: {
    "no-provenance-bypass": noBypass,
    "require-provenance-output": requireOutput,
  },
};
