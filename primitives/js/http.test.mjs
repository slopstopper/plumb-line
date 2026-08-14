// http.test.mjs — the classification core + the shared http-cases.json parity
// fixture (its Python twin is primitives/python/tests/test_http.py, same file).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseAge, classifyResponse, tagResponse, taggedFetch } from "./http.mjs";
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

// #224: mirrors test_parse_age_* in python/tests/test_http.py. The hostile
// list is byte-identical to Python's — each entry is a header value that some
// built-in coercion would accept (Number("") is 0, Number("0x10") is 16,
// Number("1e3") is 1000, Number("Infinity") is Infinity) but the shared
// AGE_DECIMAL pattern must reject, or cache detection becomes
// language-dependent (#172).
describe("parseAge", () => {
  it("rejects hostile header bytes and stays total through classification", () => {
    const hostile = [
      "\u001c60", "\u001d60", "\u001e60", "\u001f60", "\u008560", "\ufeff60",
      "\u00a060", "\u168060", "\u300060", "\u0666\u0660", "0x10", "1_000",
      "1e3", "abc", "", "   ", "-5", "+60", ".5", "60.", "Infinity", "NaN",
    ];
    for (const raw of hostile) {
      expect(parseAge(raw), JSON.stringify(raw)).toBe(null);
      // ...and the whole classification path stays total on the same input
      expect(classifyResponse(200, { Age: raw }), JSON.stringify(raw))
        .toEqual({ source: "real", confidence: "high" });
    }
  });
  it("accepts only OWS-wrapped ASCII digits", () => {
    // RFC 7230 OWS is SP/HTAB only; RFC 7234 delta-seconds is ASCII digits.
    expect(parseAge("60")).toBe(60);
    expect(parseAge(" 60 ")).toBe(60);
    expect(parseAge("\t60\t")).toBe(60);
    expect(parseAge("60.5")).toBe(60.5);
    expect(parseAge(null)).toBe(null);
  });
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
