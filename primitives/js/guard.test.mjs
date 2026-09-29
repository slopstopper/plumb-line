// guard.test.mjs — the egress guard (#120). The predicates are pinned for both
// languages by the `guard` kind in ../conformance/cases.json; this file covers
// what a case row cannot express: the exports, the error classes, the message,
// and the guard on values built by mark() and derive().
import { describe, it, expect } from "vitest";
import { guard, ProvenanceRefused, mark, derive, unwrap } from "./index.mjs";

const refusal = (fn) => {
  try {
    fn();
  } catch (e) {
    return e;
  }
  throw new Error("expected a throw");
};

describe("guard — the egress guard (#120)", () => {
  it("returns the marked value it was given, so an output point unwraps it", () => {
    const price = mark(99.99, { source: "real", confidence: "high" });
    expect(guard(price)).toBe(price);
    expect(unwrap(guard(price, { minConfidence: "high" }))).toBe(99.99);
  });

  it("refuses a value derived from mock by default, and passes it when no-mock is off", () => {
    const rate = mark(1.17, { source: "mock", confidence: "low" });
    const amount = derive([mark(100, { source: "real", confidence: "high" }), rate], (a, r) => a * r);
    const e = refusal(() => guard(amount));
    expect(e).toBeInstanceOf(ProvenanceRefused);
    expect(e.reasons.some((r) => r.startsWith("mock:"))).toBe(true);
    expect(guard(amount, { noMock: false })).toBe(amount);
  });

  it("is an Error whose message starts the same in both languages and lists every reason", () => {
    const e = refusal(() => guard(mark(1, { source: "mock", confidence: "low" }), { minConfidence: "high" }));
    expect(e).toBeInstanceOf(Error);
    expect(e.name).toBe("ProvenanceRefused");
    expect(e.message.startsWith("provenance refused: ")).toBe(true);
    expect(e.reasons).toHaveLength(2);
    for (const r of e.reasons) expect(e.message).toContain(r);
  });

  it("refuses a value that is not marked", () => {
    for (const x of [42, "text", null, undefined, [], new Map()]) {
      const e = refusal(() => guard(x));
      expect(e).toBeInstanceOf(ProvenanceRefused);
    }
  });

  it("accepts a marked value with a null prototype, as a pollution-safe JSON parser builds it", () => {
    const parsed = Object.assign(Object.create(null), mark(1, { source: "real", confidence: "high" }));
    expect(guard(parsed)).toBe(parsed);
  });

  it("raises a programmer error, not a refusal, for a bad option, before looking at the value", () => {
    for (const opts of [{ minConfidence: "hi" }, { minConfidence: 2 }, { noMock: "yes" }, { nomock: false },
      "yes", null, new Map([["noMock", false]])]) {
      const e = refusal(() => guard(42, opts));
      expect(e).toBeInstanceOf(TypeError);
      expect(e).not.toBeInstanceOf(ProvenanceRefused);
      expect(e.message.startsWith("guard: ")).toBe(true);
    }
  });

  it("names an unknown option, so a typo cannot silently turn a check off", () => {
    expect(() => guard(mark(1, { source: "real" }), { nomock: false })).toThrow(/guard: unknown option nomock/);
  });

  it("takes options only as a plain object, so an inherited value cannot turn a check off", () => {
    const m = mark(1, { source: "mock" });
    expect(() => guard(m, Object.create({ noMock: false }))).toThrow(/guard: options must be a plain object/);
  });

  it("reads only the value's own envelope fields, so a polluted prototype cannot vouch for it", () => {
    const fields = { source: "real", confidence: "high", derivedFromMock: false, lineage: [] };
    try {
      Object.assign(Object.prototype, fields);
      const e = refusal(() => guard({ value: 1 }));
      expect(e).toBeInstanceOf(ProvenanceRefused);
      expect(e.reasons.join(" ")).toMatch(/invalid envelope: missing required field: source/);
    } finally {
      for (const k of Object.keys(fields)) delete Object.prototype[k];
    }
  });

  it("refuses a value whose `value` or envelope fields are inherited, or that is a class instance", () => {
    const envelope = { source: "real", confidence: "high", derivedFromMock: false, lineage: [] };
    for (const x of [Object.assign(Object.create({ value: 1 }), envelope),
      Object.assign(Object.create({ ...envelope, value: 1 }), {}),
      Object.assign(new (class Marked {})(), { value: 1, ...envelope })]) {
      expect(() => guard(x)).toThrow(ProvenanceRefused);
    }
  });

  it("refuses a lineage step that is not a plain object, so taint in a Map cannot pass unseen", () => {
    const x = { value: 1, provenanceVersion: 2, source: "derived", confidence: "high", derivedFromMock: false,
      lineage: [new Map([["source", "mock"], ["derivedFromMock", true]])] };
    expect(() => guard(x)).toThrow(/invalid envelope: lineage step 0 is not a plain object/);
  });

  it("refuses, never throws a TypeError for, a malformed value it cannot print", () => {
    const { proxy: revoked, revoke } = Proxy.revocable({}, {});
    revoke();
    const trapping = new Proxy({}, { get() { throw new Error("trap"); } });
    for (const unprintable of [Object.assign(Object.create(null), { n: 1n }), revoked, trapping]) {
      for (const field of ["confidenceScore", "weakestSource", "source"]) {
        const x = { ...mark(1, { source: "real", confidence: "high" }), [field]: unprintable };
        expect(() => guard(x)).toThrow(ProvenanceRefused);
      }
    }
  });

  it("an undefined option is the default", () => {
    const m = mark(1, { source: "mock" });
    expect(() => guard(m, { noMock: undefined })).toThrow(ProvenanceRefused);
    expect(guard(mark(1, { source: "real" }), { minConfidence: undefined })).toBeTruthy();
  });
});
