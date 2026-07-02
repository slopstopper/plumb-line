// property.test.mjs — fast-check property tests for the combination law invariants.
import { describe, it } from "vitest";
import fc from "fast-check";
import { combineProvenance, taints, STATUS, CONFIDENCE } from "./provenance.mjs";
import { mark, derive, metaOf } from "./marked.mjs";
import { auditMeta } from "./audit.mjs";

// Arbitraries for envelope fields.
const arbSource = fc.constantFrom(...STATUS);
const arbConfidence = fc.constantFrom(...CONFIDENCE);
const arbMeta = fc.record({
  source: arbSource,
  confidence: arbConfidence,
  derivedFromMock: fc.boolean(),
  lineage: fc.constant([]),
});
// At least one input is required for the law properties.
const arbMetas = fc.array(arbMeta, { minLength: 1, maxLength: 6 });

describe("combination law properties", () => {
  it("taint is monotone: any tainted input taints the output", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        const out = combineProvenance(...metas);
        const anyTainted = metas.some(taints);
        if (anyTainted) return out.derivedFromMock === true;
        return out.derivedFromMock === false;
      }),
    );
  });

  it("confidence is monotone: output never exceeds the weakest input", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        const out = combineProvenance(...metas);
        const weakestIdx = Math.min(
          ...metas.map((m) => {
            const idx = CONFIDENCE.indexOf(m.confidence);
            return idx === -1 ? 0 : idx;
          }),
        );
        return CONFIDENCE.indexOf(out.confidence) <= weakestIdx;
      }),
    );
  });

  it("output is always source 'derived' for non-empty inputs", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        return combineProvenance(...metas).source === "derived";
      }),
    );
  });

  it("lineage length equals prior steps plus one step per input", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        const priorTotal = metas.reduce(
          (n, m) => n + (Array.isArray(m.lineage) ? m.lineage.length : 0),
          0,
        );
        const out = combineProvenance(...metas);
        return out.lineage.length === priorTotal + metas.length;
      }),
    );
  });

  it("step IDs are unique within the output lineage", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        const ids = combineProvenance(...metas).lineage.map((s) => s.id);
        return new Set(ids).size === ids.length;
      }),
    );
  });

  it("auditMeta reports no issues on direct combineProvenance output", () => {
    fc.assert(
      fc.property(arbMetas, (metas) => {
        return auditMeta(combineProvenance(...metas)).length === 0;
      }),
    );
  });
});

describe("derive law properties", () => {
  // Richer arbitrary: marked value with controlled taint.
  const arbMarkedValue = arbMeta.map((meta) =>
    mark(1, { source: meta.source, confidence: meta.confidence, derivedFromMock: meta.derivedFromMock }),
  );
  const arbMarkedPair = fc.tuple(arbMarkedValue, arbMarkedValue);

  it("taint cannot be cleared by metaOverride", () => {
    fc.assert(
      fc.property(arbMarkedPair, ([a, b]) => {
        const result = derive([a, b], (x, y) => x + y, {
          source: "real",
          confidence: "high",
          derivedFromMock: false, // attempted clear — must be ignored
        });
        const anyTainted = taints(metaOf(a)) || taints(metaOf(b));
        if (anyTainted) return result.derivedFromMock === true;
        return true;
      }),
    );
  });

  it("auditMeta reports no issues on derive output", () => {
    fc.assert(
      fc.property(arbMarkedPair, ([a, b]) => {
        const result = derive([a, b], (x, y) => x + y);
        return auditMeta(metaOf(result)).length === 0;
      }),
    );
  });

  it("confidence of derive output never exceeds the weakest input", () => {
    fc.assert(
      fc.property(arbMarkedPair, ([a, b]) => {
        const result = derive([a, b], (x, y) => x + y);
        const ma = metaOf(a);
        const mb = metaOf(b);
        const weakestIdx = Math.min(
          CONFIDENCE.indexOf(ma.confidence) === -1 ? 0 : CONFIDENCE.indexOf(ma.confidence),
          CONFIDENCE.indexOf(mb.confidence) === -1 ? 0 : CONFIDENCE.indexOf(mb.confidence),
        );
        return CONFIDENCE.indexOf(result.confidence) <= weakestIdx;
      }),
    );
  });
});
