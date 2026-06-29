"use strict";
// no-provenance-bypass — flags source-code patterns that bypass the conservative
// combination law or launder taint by hand. The static complement to the runtime
// auditMeta(); see primitives/SPEC.md (PB1–PB4) for the catalogue.
//
// Placement note: this lints correct *use* of one specific library, so unlike the
// domain-neutral boundary adapter it is library-coupled. It lives under adapters/
// for now (enforcement) and may move to primitives/ in a future version.
//
// Discipline: fires only at resolved primitive call sites, only on literal field
// values. Anything dynamic is left alone — under-claim over false positives.

const DEFAULT_CLEAN_SOURCES = ["real", "semiReal", "fallback"];
// Imports counted as the primitive: the package, or its module files by basename.
const PRIMITIVE_SOURCE = /plumb-line-provenance|(?:^|\/)(?:index|marked|provenance)\.mjs$/;
// Imported names we track, mapped to the role used by the rule logic.
const TRACKED = ["mark", "derive", "makeMeta", "unwrap"];

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Flag source patterns that bypass the provenance combination law or launder taint by hand.",
      recommended: true,
    },
    schema: [
      {
        type: "object",
        properties: { sources: { type: "array", items: { type: "string" } } },
        additionalProperties: false,
      },
    ],
    messages: {
      pb1: "PB1 laundered meta: clean source '{{source}}' asserted on an explicitly mock-tainted value. Labeling cannot clear taint — derive from real inputs or keep the honest source. (SPEC §5 laundering)",
      pb2: "PB2 manual taint clear: derivedFromMock:false is ignored by the law and signals laundering intent. Remove it; taint propagates automatically. (SPEC §3)",
      pb3: "PB3 clean source override: relabeling a derived value as '{{source}}' launders it. Drop the override; the law sets source:'derived'. (SPEC §3 rule 4 / §5)",
      pb4: "PB4 re-mark of an unwrapped value: wrapping an unwrapped value in a fresh meta drops its lineage. Use derive() so provenance propagates. (SPEC §4 / §5 unreproducible)",
    },
  },

  create(context) {
    const opts = context.options[0] || {};
    const cleanSources = new Set(opts.sources || DEFAULT_CLEAN_SOURCES);

    // local-name -> tracked role (handles `import { mark as m }`)
    const localFn = new Map();
    const namespaces = new Set(); // `import * as pl` locals

    function noteImport(node) {
      const src = node.source && node.source.value;
      if (typeof src !== "string" || !PRIMITIVE_SOURCE.test(src)) return;
      for (const spec of node.specifiers) {
        if (spec.type === "ImportSpecifier") {
          if (TRACKED.includes(spec.imported.name)) {
            localFn.set(spec.local.name, spec.imported.name);
          }
        } else if (spec.type === "ImportNamespaceSpecifier") {
          namespaces.add(spec.local.name);
        }
      }
    }

    // Which primitive role, if any, this callee resolves to.
    function calleeRole(callee) {
      if (callee.type === "Identifier") return localFn.get(callee.name) || null;
      if (
        callee.type === "MemberExpression" &&
        !callee.computed &&
        callee.object.type === "Identifier" &&
        namespaces.has(callee.object.name) &&
        callee.property.type === "Identifier" &&
        TRACKED.includes(callee.property.name)
      ) {
        return callee.property.name;
      }
      return null;
    }

    function getProp(obj, name) {
      if (!obj || obj.type !== "ObjectExpression") return null;
      for (const p of obj.properties) {
        if (p.type !== "Property" || p.computed) continue;
        const key =
          p.key.type === "Identifier"
            ? p.key.name
            : p.key.type === "Literal"
              ? p.key.value
              : null;
        if (key === name) return p.value;
      }
      return null;
    }
    const isCleanSource = (n) =>
      n && n.type === "Literal" && typeof n.value === "string" && cleanSources.has(n.value);
    const isBool = (n, v) => n && n.type === "Literal" && n.value === v;

    // Only the import-bound unwrap(x) form is unambiguous — you unwrap nothing
    // but a marked value. A bare `x.value` access cannot be proven to hold a
    // marked value without dataflow (it is just as likely a raw incoming field),
    // so it is out of scope: zero false positives over catching every manual unwrap.
    function isUnwrapped(arg) {
      return Boolean(arg) && arg.type === "CallExpression" && calleeRole(arg.callee) === "unwrap";
    }

    return {
      ImportDeclaration: noteImport,
      CallExpression(node) {
        const role = calleeRole(node.callee);
        if (!role) return;

        if (role === "mark" || role === "makeMeta") {
          // meta object is the 2nd arg of mark(value, meta), the 1st of makeMeta(meta)
          const metaObj = role === "mark" ? node.arguments[1] : node.arguments[0];
          const source = getProp(metaObj, "source");
          const dfm = getProp(metaObj, "derivedFromMock");
          // PB1 only here: a literal derivedFromMock:false on mark/makeMeta is the
          // honest stored default (there is no upstream taint to clear), so PB2
          // applies only to derive overrides, where it is a genuine no-op.
          if (isCleanSource(source) && isBool(dfm, true)) {
            context.report({ node: metaObj, messageId: "pb1", data: { source: source.value } });
          }
          if (role === "mark" && isUnwrapped(node.arguments[0])) {
            context.report({ node: node.arguments[0], messageId: "pb4" });
          }
        } else if (role === "derive") {
          const override = node.arguments[2];
          const source = getProp(override, "source");
          const dfm = getProp(override, "derivedFromMock");
          if (isCleanSource(source)) {
            context.report({ node: source, messageId: "pb3", data: { source: source.value } });
          }
          if (isBool(dfm, false)) {
            context.report({ node: dfm, messageId: "pb2" });
          }
        }
      },
    };
  },
};
