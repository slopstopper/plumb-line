import { RuleTester } from "eslint";
import { afterAll, describe, it } from "vitest";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const rule = require("../require-provenance-output.cjs");

RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester({
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
});
const IMPORT = `import { mark, derive } from "../index.mjs";\n`;

ruleTester.run("require-provenance-output", rule, {
  valid: [
    // Returns a derive() call directly.
    IMPORT + `export function f(x, r) { return derive([x, r], (p, q) => p * q); }`,
    // Returns a local holding a derive() result.
    IMPORT + `export function f(x, r) { const t = derive([x, r], (p, q) => p * q); return t; }`,
    // Returns a parameter — unclassifiable, must stay silent.
    IMPORT + `export function f(marked) { return marked; }`,
    // Returns an unknown call — unclassifiable, silent.
    IMPORT + `export function f(x) { return compute(x); }`,
    // Returns a member/property — unclassifiable, silent.
    IMPORT + `export function f(o) { return o.total; }`,
    // Not exported — out of scope entirely.
    IMPORT + `function helper(x, r) { return x * r; }`,
    // The transform callback returns raw p+q, but it is nested/not exported → silent.
    IMPORT + `export function f(x, r) { return derive([x, r], (p, q) => p + q); }`,
    // Returns a literal constant — not a raw *computation*, silent.
    IMPORT + `export function f() { return 0; }`,
  ],
  invalid: [
    {
      // Direct raw arithmetic return.
      code: IMPORT + `export function f(x, r) { return x * r; }`,
      errors: [{ messageId: "untagged" }],
    },
    {
      // Raw arithmetic through a local variable.
      code: IMPORT + `export function f(x, r) { const t = x * r; return t; }`,
      errors: [{ messageId: "untagged" }],
    },
    {
      // Exported arrow assigned to a const.
      code: IMPORT + `export const f = (x, r) => { const t = x + r; return t; };`,
      errors: [{ messageId: "untagged" }],
    },
    {
      // export default function.
      code: IMPORT + `export default function (x, r) { return x - r; }`,
      errors: [{ messageId: "untagged" }],
    },
  ],
});
