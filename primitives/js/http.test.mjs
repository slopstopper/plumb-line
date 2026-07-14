// http.test.mjs — the classification core + the shared http-cases.json parity
// fixture (its Python twin is primitives/python/tests/test_http.py, same file).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { classifyResponse } from "./http.mjs";

const cases = JSON.parse(
  readFileSync(fileURLToPath(new URL("../conformance/http-cases.json", import.meta.url)), "utf8"),
);

describe("classifyResponse — shared fixture", () => {
  for (const c of cases.classify) {
    it(c.name, () => {
      expect(classifyResponse(c.status, c.headers, c.fromCache)).toEqual(c.expect);
    });
  }
});

describe("classifyResponse — header access", () => {
  it("accepts a Headers-like object with .get()", () => {
    const h = new Headers({ Age: "60" });
    expect(classifyResponse(200, h, false)).toEqual({ source: "real", confidence: "medium" });
  });
});
