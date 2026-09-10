"use strict";
// require-provenance-output — within a declared surface (the files this rule is
// enabled on), flag an EXPORTED function whose return value is a provably-raw
// computation that was never tagged by mark/derive. The opt-out complement to
// no-provenance-bypass: that rule catches laundering present; this one catches a
// trust-bearing output absent. See ADR-0011.
//
// Discipline (zero false positives): "raw" is only a binary arithmetic/string
// expression (a * r), directly or via a same-function local. A return of ANY
// call, a parameter, or a member access is NOT flagged — proving those untagged
// needs cross-file dataflow the rule deliberately omits.
//
// This rule does not consult imports. Its verdict depends on expression shape
// alone: whether mark/derive is imported, and from where, cannot change it,
// because a call is never a binary expression. An earlier version carried the
// bypass rule's import tracking (noteImport / a "tagged" class / the
// modules+tracked options) and none of it had an observable effect — the
// "tagged" class was set and never read, so the options were advertised and
// dead (#212). They are removed rather than kept as a no-op: an option that
// silently does nothing is the overstated capability P6 forbids. The bypass
// rule (no-provenance-bypass) genuinely uses tracking and keeps those options.

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Within declared files, require exported functions to tag their output with mark/derive.",
      recommended: false,
    },
    schema: [],
    messages: {
      untagged:
        "Untagged output: this exported function returns a raw computed value not wrapped by mark/derive. Wrap the returned value with derive()/mark() so provenance propagates. (ADR-0011)",
    },
  },

  create(context) {
    const RAW_OPS = new Set(["+", "-", "*", "/", "%", "**", "&", "|", "^", "<<", ">>", ">>>"]);
    const isRaw = (n) => n && n.type === "BinaryExpression" && RAW_OPS.has(n.operator);

    // Classify a function body's returns using single-pass local const/let tracking.
    function checkFunctionBody(fnNode) {
      if (!fnNode.body || fnNode.body.type !== "BlockStatement") {
        // Concise arrow body: `=> expr`. Flag iff expr is raw.
        if (fnNode.body && isRaw(fnNode.body)) {
          context.report({ node: fnNode.body, messageId: "untagged" });
        }
        return;
      }
      const localClass = new Map(); // name -> "raw" (anything else is unknown: silent)
      const assignedCount = new Map(); // name -> value-binding assignments (>1 ⇒ unknown)
      // Count every value-binding assignment to a simple local — a `const/let x =`
      // declarator AND a later plain `x = ...` reassignment. A name assigned more
      // than once is demoted to unknown (silent): we cannot know statically which
      // value it holds at the return. This mirrors the Python checker's
      // pop-on-reassignment and is what keeps `let out = x*r; out = mark(out);
      // return out` from being flagged (a false positive on already-tagged code).
      const noteAssign = (name, valueNode) => {
        const n = (assignedCount.get(name) || 0) + 1;
        assignedCount.set(name, n);
        if (n > 1) { localClass.delete(name); return; }
        if (isRaw(valueNode)) localClass.set(name, "raw");
      };
      for (const stmt of fnNode.body.body) {
        if (stmt.type === "VariableDeclaration") {
          for (const d of stmt.declarations) {
            if (d.id.type !== "Identifier" || !d.init) continue;
            noteAssign(d.id.name, d.init);
          }
        } else if (
          stmt.type === "ExpressionStatement" &&
          stmt.expression.type === "AssignmentExpression" &&
          stmt.expression.operator === "=" &&
          stmt.expression.left.type === "Identifier"
        ) {
          noteAssign(stmt.expression.left.name, stmt.expression.right);
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
