// http.mjs — HTTP ingestion adapter for JS `fetch`. Auto-tags a Response with a
// provenance envelope by status + cache state (see ADR-0012). The classification
// core is dependency-free; `fetch`/`Response` are native (Node >= 18 / browsers).
// The tagger/wrapper live in this file too (added in a later task).

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

function isCached(status, headers, fromCache) {
  if (fromCache) return true;
  if (status === 304) return true;
  const age = header(headers, "age");
  if (age != null) {
    const n = Number(age);
    if (Number.isFinite(n) && n > 0) return true;
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
