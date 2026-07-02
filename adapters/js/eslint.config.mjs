import js from "@eslint/js";
import globals from "globals";

// ESLint (recommended) as a CI gate for the JS enforcement adapters. Satisfies
// OpenSSF Best Practices silver: coding_standards_enforced, warnings_strict.
//
// The *.template.cjs files are ESLint *config templates* shipped for host
// projects to copy; they reference plugins resolved in the host, not here, so
// they are not linted as source.
export default [
  {
    ignores: [
      "coverage/**",
      "node_modules/**",
      "**/*.template.cjs",
    ],
  },
  js.configs.recommended,
  {
    files: ["**/*.mjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.node },
    },
    rules: {
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],
    },
  },
  {
    files: ["**/*.cjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "commonjs",
      globals: { ...globals.node },
    },
  },
];
