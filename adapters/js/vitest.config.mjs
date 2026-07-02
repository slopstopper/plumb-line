import { defineConfig } from "vitest/config";

// Coverage runs as part of the plain `npm test` CI/release already invoke, so
// the statement-coverage floor is enforced without a separate step. The pure
// decision logic (decide(), the ESLint rule) is unit-tested; the process-entry
// CLI wrappers are marked with `v8 ignore` because v8's in-process
// instrumentation can't see across the spawned child the CLI tests use.
// See OpenSSF `test_statement_coverage80`.
export default defineConfig({
  test: {
    coverage: {
      enabled: true,
      provider: "v8",
      include: ["hooks/**/*.mjs", "provenance-lint/**/*.cjs"],
      exclude: ["**/__tests__/**", "**/*.template.cjs"],
      all: true,
      reporter: ["text", "text-summary"],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
});
