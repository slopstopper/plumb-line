// conformance.test.mjs — runs the shared cases.json against the JS primitive.
// Its Python twin (primitives/python/test_conformance.py) runs the SAME file;
// together they make JS/Python parity a data contract, not a prose promise.
//
// The cases are judged by run-cases.mjs, the one JS interpreter of
// cases.json that report.mjs and the bundle check also use (#369, #430):
// this file only turns each result into a named vitest case, so the suite,
// the self-certification gate and the bundle check cannot read a case
// differently.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as impl from "./index.mjs";
import { runCases } from "../conformance/run-cases.mjs";

const cases = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../conformance/cases.json", import.meta.url)),
    "utf8",
  ),
);

const results = runCases(impl, cases);

describe("conformance — the runner judged every case", () => {
  it("one result per case, plus nothing unexpected", () => {
    const perKind = cases.combine.length + cases.audit.length + cases.validate.length;
    expect(results.length).toBe(perKind);
  });
});

for (const kind of [...new Set(results.map((r) => r.kind))]) {
  describe(`conformance — ${kind}`, () => {
    for (const r of results.filter((x) => x.kind === kind)) {
      it(r.name, () => {
        expect(r.error, r.error ?? "").toBeNull();
      });
    }
  });
}
