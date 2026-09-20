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
    // Nested return inside an if-branch — top-level-only scan, silent (I3 parity).
    IMPORT + `export function f(x, r, c) { if (c) return x * r; return 0; }`,
    // C1 guard: local re-tagged inside the branch before being returned there.
    IMPORT + `export function f(x, r, cond) { let t = x * r; if (cond) { t = derive([x, r], g); return t; } return 0; }`,
    // I2 guard: comparison operator is not arithmetic/bitwise, must stay silent.
    IMPORT + `export function f(a, b) { return a === b; }`,
    // #212: the rule does not consult imports. A returned call is unclassifiable
    // and silent whether or not mark/derive is imported, and wherever from.
    `export function f(x) { return mark(x, { source: "real" }); }`,
    `export function f(x, r) { const t = derive([x, r], g); return t; }`,
    `import { mark } from "@myorg/data";\nexport function f(x) { return mark(x, { source: "real" }); }`,
    // Reassignment guard: raw local re-tagged in place via plain assignment must
    // NOT be flagged — the reassignment demotes it to unknown (mirrors Python).
    IMPORT + `export function f(x, r) { let out = x * r; out = mark(out, { source: "derived" }); return out; }`,
    // Symmetric: tagged local reassigned to raw is also demoted to unknown → silent.
    IMPORT + `export function f(x, r) { let t = derive([x, r], g); t = x * r; return t; }`,
  ],
  invalid: [
    // Direct raw return.
    { code: IMPORT + `export function f(x, r) { return x * r; }`,
      errors: [{ messageId: "untagged", data: { name: "f" } }] },
    // Raw via a local.
    { code: IMPORT + `export function f(x, r) { const t = x * r; return t; }`,
      errors: [{ messageId: "untagged", data: { name: "f" } }] },
    // Concise arrow body on an exported const.
    { code: IMPORT + `export const g = (x, r) => x * r;`,
      errors: [{ messageId: "untagged", data: { name: "g" } }] },
    // Function expression on an exported const.
    { code: IMPORT + `export const h = function (x, r) { return x - r; };`,
      errors: [{ messageId: "untagged", data: { name: "h" } }] },
    // Named default export.
    { code: IMPORT + `export default function named(x, r) { return x / r; }`,
      errors: [{ messageId: "untagged", data: { name: "named" } }] },
    // Anonymous default export → "default".
    { code: IMPORT + `export default (x, r) => x % r;`,
      errors: [{ messageId: "untagged", data: { name: "default" } }] },
    // Anonymous default function expression → "default".
    { code: IMPORT + `export default function (x, r) { return x ** r; }`,
      errors: [{ messageId: "untagged", data: { name: "default" } }] },
    // Two raw returns in one function: two reports, same site name.
    { code: IMPORT + `export function two(x, r) { const t = x * r; return t; return x + r; }`,
      errors: [{ messageId: "untagged", data: { name: "two" } }, { messageId: "untagged", data: { name: "two" } }] },
    // The rendered text ends with the site marker the SARIF assembler extracts.
    { code: IMPORT + `export function f(x, r) { return x * r; }`,
      errors: [{ message: /\[site: f\]$/ }] },
    // Exported arrow with a block body (not concise) assigned to a const.
    { code: IMPORT + `export const f = (x, r) => { const t = x + r; return t; };`,
      errors: [{ messageId: "untagged", data: { name: "f" } }] },
    // export default function, anonymous, another operator.
    { code: IMPORT + `export default function (x, r) { return x - r; }`,
      errors: [{ messageId: "untagged", data: { name: "default" } }] },
    // #212: a raw return is flagged with NO primitive import in the file —
    // the verdict is expression shape alone.
    { code: `export function f(x, r) { return x * r; }`,
      errors: [{ messageId: "untagged", data: { name: "f" } }] },
    // #390: a destructuring declarator (non-Identifier id) gets a stable
    // name derived from the pattern's source text, never the literal
    // "default" — a real anonymous default export in the same file must
    // remain a distinct site.
    { code: IMPORT + `export const { a } = () => x * r;`,
      errors: [{ messageId: "untagged", data: { name: "destructured { a }" } }] },
    { code: IMPORT + `export const { a } = () => x * r;\nexport default (x, r) => x % r;`,
      errors: [
        { messageId: "untagged", data: { name: "destructured { a }" } },
        { messageId: "untagged", data: { name: "default" } },
      ] },
  ],
});

describe("require-provenance-output takes no options (#212)", () => {
  it("declares an empty schema — modules/tracked were advertised and dead", () => {
    if (!Array.isArray(rule.meta.schema) || rule.meta.schema.length !== 0) {
      throw new Error(`expected schema [], got ${JSON.stringify(rule.meta.schema)}`);
    }
  });
});
