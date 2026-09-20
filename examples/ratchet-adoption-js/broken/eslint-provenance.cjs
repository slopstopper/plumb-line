// Standalone flat config for this fixture (#393). A consumer's own config
// require()s wherever it copied adapters/js/provenance-lint/ to; this fixture
// lives inside the plumb-line checkout, so it reaches the adapter by relative
// path instead — no install of the plugin, only of ESLint itself.
//
// The path is explicit down to index.cjs on purpose: Node's directory-index
// resolution only tries index.js/.json/.node — NOT index.cjs — so a bare
// require() of the directory throws MODULE_NOT_FOUND.
const provenance = require("../../../adapters/js/provenance-lint/index.cjs");

module.exports = [
  {
    // The declared output surface — the same set the manifest's outputGlobs
    // name. Inside it every exported function is checked; outside it the rule
    // does not exist.
    files: ["src/pricing/**/*.js"],
    plugins: { "plumb-line": provenance },
    languageOptions: { ecmaVersion: 2022, sourceType: "module" },
    rules: { "plumb-line/require-provenance-output": "error" },
  },
];
