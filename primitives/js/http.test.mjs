// http.test.mjs — the classification core + the shared http-cases.json parity
// fixture (its Python twin is primitives/python/tests/test_http.py, same file).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { classifyResponse, tagResponse, taggedFetch } from "./http.mjs";
import { metaOf, unwrap } from "./marked.mjs";

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

describe("tagResponse", () => {
  it("tags a fresh 200 as real/high", () => {
    const r = new Response("{}", { status: 200 });
    const m = tagResponse(r);
    expect(metaOf(m).source).toBe("real");
    expect(metaOf(m).confidence).toBe("high");
    expect(unwrap(m)).toBe(r); // the response is the marked value
  });
  it("tags a stale cache hit as real/medium", () => {
    const r = new Response("{}", { status: 200, headers: { Age: "60" } });
    expect(metaOf(tagResponse(r))).toMatchObject({ source: "real", confidence: "medium" });
  });
  it("tags a 500 as unavailable/none", () => {
    const r = new Response("", { status: 500 });
    expect(metaOf(tagResponse(r))).toMatchObject({ source: "unavailable", confidence: "none" });
  });
});

describe("taggedFetch", () => {
  it("fetches then tags", async () => {
    const orig = globalThis.fetch;
    globalThis.fetch = async () => new Response("{}", { status: 200 });
    try {
      const m = await taggedFetch("https://example.test/data");
      expect(metaOf(m)).toMatchObject({ source: "real", confidence: "high" });
    } finally {
      globalThis.fetch = orig;
    }
  });
});
