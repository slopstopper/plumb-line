import { defineConfig } from "vitest/config";

// Coverage is enabled here so the plain `npm test` (vitest run) that CI and the
// release workflow already invoke also enforces the statement-coverage floor —
// no separate command or workflow step to keep in sync. OpenSSF Best Practices
// (silver) `test_statement_coverage80` asks for >=80% statement coverage; we
// gate above that.
export default defineConfig({
  test: {
    coverage: {
      enabled: true,
      provider: "v8",
      include: ["*.mjs"],
      exclude: ["vitest.config.mjs", "**/*.test.mjs"],
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
