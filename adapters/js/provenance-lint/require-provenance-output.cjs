"use strict";
// require-provenance-output — within a declared surface (the files this rule is
// enabled on), flag an EXPORTED function whose return value is a provably-raw
// computation that was never tagged by mark/derive. The opt-out complement to
// no-provenance-bypass: that rule catches laundering present; this one catches a
// trust-bearing output absent. See ADR-0011.
//
// Discipline (zero false positives): "raw" is only a binary arithmetic/string
// expression (a * r), directly or via a same-function local. A return of a
// tracked call, a parameter, an unknown call, or a member access is NOT flagged —
// proving those untagged needs cross-file dataflow the rule deliberately omits.
const { normalizeModuleName, matchesExtraModule } = require("./module-match.cjs");

const PRIMITIVE_SOURCE = /plumb-line-provenance|(?:^|\/)(?:index|marked|provenance)\.mjs$/;
const TRACKED = ["mark", "derive", "makeMeta", "unwrap"];

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Within declared files, require exported functions to tag their output with mark/derive.",
      recommended: false,
    },
    schema: [
      {
        type: "object",
        properties: {
          modules: { type: "array", items: { type: "string" } },
          tracked: {
            type: "object",
            additionalProperties: { enum: ["mark", "derive", "makeMeta", "unwrap"] },
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      untagged:
        "Untagged output: this exported function returns a raw computed value not wrapped by mark/derive. Wrap the returned value with derive()/mark() so provenance propagates. (ADR-0011)",
    },
  },

  create(context) {
    const opts = context.options[0] || {};
    const extraModules = new Set((opts.modules || []).map(normalizeModuleName));
    const trackedRoles = new Map(TRACKED.map((n) => [n, n]));
    for (const [name, role] of Object.entries(opts.tracked || {})) trackedRoles.set(name, role);
    const isPrimitiveSource = (src) =>
      PRIMITIVE_SOURCE.test(src) || matchesExtraModule(src, extraModules);

    const localFn = new Map(); // local import name -> role
    function noteImport(node) {
      const src = node.source && node.source.value;
      if (typeof src !== "string" || !isPrimitiveSource(src)) return;
      for (const spec of node.specifiers) {
        if (spec.type === "ImportSpecifier" && trackedRoles.has(spec.imported.name)) {
          localFn.set(spec.local.name, trackedRoles.get(spec.imported.name));
        }
      }
    }
    const isTrackedCall = (n) =>
      n && n.type === "CallExpression" && n.callee.type === "Identifier" &&
      Boolean(localFn.get(n.callee.name));
    const isRaw = (n) => n && n.type === "BinaryExpression";

    // Classify a function body's returns using single-pass local const/let tracking.
    function checkFunctionBody(fnNode) {
      if (!fnNode.body || fnNode.body.type !== "BlockStatement") {
        // Concise arrow body: `=> expr`. Flag iff expr is raw.
        if (fnNode.body && isRaw(fnNode.body)) {
          context.report({ node: fnNode.body, messageId: "untagged" });
        }
        return;
      }
      const localClass = new Map(); // name -> "raw" | "tagged"
      const assignedOnce = new Map(); // name -> count (>1 ⇒ downgrade to unknown)
      for (const stmt of fnNode.body.body) {
        if (stmt.type === "VariableDeclaration") {
          for (const d of stmt.declarations) {
            if (d.id.type !== "Identifier" || !d.init) continue;
            const n = (assignedOnce.get(d.id.name) || 0) + 1;
            assignedOnce.set(d.id.name, n);
            if (n > 1) { localClass.delete(d.id.name); continue; }
            if (isTrackedCall(d.init)) localClass.set(d.id.name, "tagged");
            else if (isRaw(d.init)) localClass.set(d.id.name, "raw");
          }
        }
      }
      for (const stmt of fnNode.body.body) {
        if (stmt.type !== "ReturnStatement" || !stmt.argument) continue;
        const arg = stmt.argument;
        if (isRaw(arg)) context.report({ node: arg, messageId: "untagged" });
        else if (arg.type === "Identifier" && localClass.get(arg.name) === "raw") {
          context.report({ node: arg, messageId: "untagged" });
        }
      }
    }

    // Only EXPORTED functions are in scope.
    function handleExportedFn(fnNode) {
      if (!fnNode) return;
      if (fnNode.type === "FunctionDeclaration" || fnNode.type === "FunctionExpression" ||
          fnNode.type === "ArrowFunctionExpression") {
        checkFunctionBody(fnNode);
      }
    }

    return {
      ImportDeclaration: noteImport,
      ExportNamedDeclaration(node) {
        if (node.declaration && node.declaration.type === "FunctionDeclaration") {
          handleExportedFn(node.declaration);
        } else if (node.declaration && node.declaration.type === "VariableDeclaration") {
          for (const d of node.declaration.declarations) {
            if (d.init && (d.init.type === "ArrowFunctionExpression" || d.init.type === "FunctionExpression")) {
              handleExportedFn(d.init);
            }
          }
        }
      },
      ExportDefaultDeclaration(node) {
        const d = node.declaration;
        if (d && (d.type === "FunctionDeclaration" || d.type === "FunctionExpression" ||
                  d.type === "ArrowFunctionExpression")) {
          handleExportedFn(d);
        }
      },
    };
  },
};
