// http.mjs — HTTP ingestion adapter for JS `fetch`. Auto-tags a Response with a
// provenance envelope by status + cache state (see ADR-0012). The classification
// core is dependency-free; `fetch`/`Response` are native (Node >= 18 / browsers).
// The tagger/wrapper live in this file too.
import { mark } from "./marked.mjs";

// Case-insensitive header read supporting both a Headers-like object (.get) and
// a plain object.
function header(headers, name) {
  if (!headers) return null;
  if (typeof headers.get === "function") return headers.get(name);
  const want = name.toLowerCase();
  for (const k of Object.keys(headers)) {
    if (k.toLowerCase() === want) return headers[k];
  }
  return null;
}

// Age is RFC 7234 delta-seconds: a decimal number. Parsed by an explicit pattern
// rather than Number()/float() because the two languages' built-in coercions
// disagree on non-decimal strings — Number("0x10") is 16 while Python's
// float("0x10") raises, and Number("1_000") is NaN while float("1_000") is 1000.
// Either coercion would make cache detection language-dependent (#172). A
// fractional part is tolerated because some proxies emit one and it is already
// pinned in the conformance table; anything else reads as "no usable Age".
// Returns a number, or null when the header is not a decimal value.
const AGE_DECIMAL = /^\s*\d+(\.\d+)?\s*$/;

export function parseAge(raw) {
  if (raw == null) return null;
  const s = String(raw);
  if (!AGE_DECIMAL.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function isCached(status, headers, fromCache) {
  if (fromCache) return true;
  if (status === 304) return true;
  const age = header(headers, "age");
  if (age != null) {
    const n = parseAge(age);
    if (n !== null && n > 0) return true;
  }
  const xCache = header(headers, "x-cache");
  if (xCache != null && String(xCache).toUpperCase().includes("HIT")) return true;
  return false;
}

// Map an HTTP response to (source, confidence). source = origin trust,
// confidence = freshness. A cache hit stays `real`, only its confidence drops.
// Never emits `fallback` (reserved for caller-supplied substitutes).
export function classifyResponse(status, headers, fromCache = false) {
  const cached = isCached(status, headers, fromCache);
  if (status === 304) return { source: "real", confidence: "medium" };
  if (status >= 200 && status < 300) {
    return cached
      ? { source: "real", confidence: "medium" }
      : { source: "real", confidence: "high" };
  }
  return { source: "unavailable", confidence: "none" };
}

// Tag a native Response with a provenance envelope by status/cache. The marked
// value is the Response; extract via `derive([tagged], (r) => r.json())`.
// Requires a runtime with global `Response`/`fetch` (Node >= 18 / browsers).
export function tagResponse(response, fromCache = false) {
  const { source, confidence } = classifyResponse(response.status, response.headers, fromCache);
  return mark(response, { source, confidence });
}

// Fetch with the native `fetch` and tag the response in one call.
export async function taggedFetch(url, options) {
  return tagResponse(await fetch(url, options));
}
