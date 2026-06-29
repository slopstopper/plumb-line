import { RuleTester } from "eslint";
import { afterAll, describe, it } from "vitest";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const rule = require("../no-provenance-bypass.cjs");

// Wire ESLint's RuleTester to vitest's runner (no global describe/it here).
RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester({
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
});

const IMPORT = `import { mark, derive, makeMeta, unwrap } from "../index.mjs";\n`;

ruleTester.run("no-provenance-bypass", rule, {
  valid: [
    // Honest usage: derive propagates, no hand-built laundering.
    IMPORT + `const t = derive([a, b], (x, y) => x + y);`,
    IMPORT + `const m = mark(1000, { source: "real", confidence: "high" });`,
    IMPORT + `const m = mark(2, { source: "mock", confidence: "low" });`,
    // derivedFromMock:true on a non-clean source is honest, not laundering.
    IMPORT + `const m = mark(2, { source: "mock", derivedFromMock: true });`,
    // A non-clean source override on derive is allowed (still labelled derived-ish).
    IMPORT + `const t = derive([a], (x) => x, { confidence: "low" });`,
    // Same call shapes but NOT imported from the primitive → must not fire.
    `import { mark } from "./my-utils.js";\nconst m = mark(x.value, { source: "real", derivedFromMock: true });`,
    // Dynamic field values cannot be proven → stay silent (under-claim).
    IMPORT + `const m = mark(1, { source: src, derivedFromMock: flag });`,
    // derivedFromMock:false on mark is the honest stored default, not laundering (PB2 is derive-only).
    IMPORT + `const m = mark(1000, { source: "real", derivedFromMock: false });`,
    // mark of a raw `.value` field cannot be proven a marked value → not PB4.
    IMPORT + `const m = mark(apiResponse.value, { source: "real", confidence: "high" });`,
  ],
  invalid: [
    {
      // PB1 — clean source asserted on an explicitly tainted value
      code: IMPORT + `const m = mark(42, { source: "real", derivedFromMock: true });`,
      errors: [{ messageId: "pb1", data: { source: "real" } }],
    },
    {
      // PB1 via makeMeta (meta is the 1st arg)
      code: IMPORT + `const meta = makeMeta({ source: "fallback", derivedFromMock: true });`,
      errors: [{ messageId: "pb1" }],
    },
    {
      // PB2 — manual taint clear on a derive override (a genuine no-op)
      code: IMPORT + `const t = derive([a], (x) => x, { derivedFromMock: false });`,
      errors: [{ messageId: "pb2" }],
    },
    {
      // PB3 — clean source override on derive
      code: IMPORT + `const t = derive([a, b], (x, y) => x + y, { source: "real" });`,
      errors: [{ messageId: "pb3", data: { source: "real" } }],
    },
    {
      // PB4 — re-mark of an unwrapped value (the unambiguous unwrap(x) form)
      code: IMPORT + `const m = mark(unwrap(other), { confidence: "high" });`,
      errors: [{ messageId: "pb4" }],
    },
    {
      // aliased import still resolves
      code:
        `import { mark as m } from "plumb-line-provenance";\n` +
        `const x = m(1, { source: "semiReal", derivedFromMock: true });`,
      errors: [{ messageId: "pb1", data: { source: "semiReal" } }],
    },
    {
      // namespace import: pl.derive(..., { source: clean })
      code:
        `import * as pl from "../index.mjs";\n` +
        `const t = pl.derive([a], (x) => x, { source: "real" });`,
      errors: [{ messageId: "pb3" }],
    },
  ],
});
