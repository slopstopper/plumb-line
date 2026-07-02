import js from "@eslint/js";
import globals from "globals";

// ESLint (recommended) as a CI gate for the published JS primitive — the
// PEP-8-equivalent for the JavaScript side of CONTRIBUTING.md. Satisfies
// OpenSSF Best Practices silver: coding_standards_enforced, warnings_strict.
export default [
  { ignores: ["coverage/**", "node_modules/**"] },
  js.configs.recommended,
  {
    files: ["**/*.mjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.node },
    },
    rules: {
      // Allow the idiomatic omit-a-key rest pattern: `const { drop, ...rest } = o`.
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],
    },
  },
];
