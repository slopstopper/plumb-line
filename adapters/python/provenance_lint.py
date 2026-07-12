"""provenance_lint — static checker for provenance-bypass patterns (SPEC PB1-PB4).

The stdlib-`ast` complement to the runtime audit_meta(): it flags the source-code
patterns that launder taint or bypass the conservative-combination law, before the
code runs. Mirror of the JS ESLint rule no-provenance-bypass; the two enforce the
same four rules in language-idiomatic form (Python passes meta as keyword
arguments, JS as an object literal).

Placement note: this lints correct *use* of one specific library, so unlike the
domain-neutral boundary adapter it is library-coupled. It lives under adapters/
for now (enforcement) and may move to primitives/ in a future version.

Discipline: fires only at resolved primitive call sites, only on literal field
values. Anything dynamic is left alone — under-claim over false positives.

Usage:
    python3 provenance_lint.py path/to/file.py [more.py ...]
    # exits non-zero if any issue is found; prints `file:line: RULE message`.
"""
import ast
import sys

CLEAN_SOURCES = {'real', 'semiReal', 'fallback'}
PRIMITIVE_MODULES = {'plumb_line_provenance', 'marked', 'provenance'}
TRACKED = {'mark', 'derive', 'make_meta', 'unwrap'}

MESSAGES = {
    'PB1': "PB1 laundered meta: clean source '{source}' with derived_from_mock=True. "
           "Labeling cannot clear taint — derive from real inputs or keep the honest source. (SPEC §5 laundering)",
    'PB2': "PB2 manual taint clear: derived_from_mock=False is ignored by the law and signals "
           "laundering intent. Remove it; taint propagates automatically. (SPEC §3)",
    'PB3': "PB3 clean source override: relabeling a derived value as '{source}' launders it. "
           "Drop the override; the law sets source='derived'. (SPEC §3 rule 4 / §5)",
    'PB4': "PB4 re-mark of an unwrapped value: wrapping an unwrapped value in fresh meta drops its "
           "lineage. Use derive() so provenance propagates. (SPEC §4 / §5 unreproducible)",
}

_OUTPUT_MESSAGE = ("REQ-OUTPUT untagged output: this module-level function returns a raw "
                   "computed value not wrapped by mark/derive. Wrap the returned value with "
                   "derive()/mark() so provenance propagates. (ADR-0011)")

_EXT = ('.mjs', '.cjs', '.js', '.py')

def _normalize_module_name(module):
    base = (module or '').split('.')[-1]
    for ext in _EXT:
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    return base.replace('_', '-')

# Back-compat alias used by import collection.
_basename = _normalize_module_name


def _keyword(call, name):
    """The value node of keyword `name` on a call, or None (ignores **kwargs)."""
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_const_bool(node, value):
    return isinstance(node, ast.Constant) and node.value is value


class _Visitor(ast.NodeVisitor):
    def __init__(self, clean_sources=None, primitive_modules=None, tracked=None):
        self.clean_sources = clean_sources if clean_sources is not None else CLEAN_SOURCES
        self.primitive_modules = primitive_modules if primitive_modules is not None else PRIMITIVE_MODULES
        # name -> role; the built-in names are their own role.
        self.tracked = tracked if tracked is not None else {n: n for n in TRACKED}
        self.local_fn = {}      # local name -> tracked role
        self.namespaces = set()  # locals bound to a primitive module
        self.issues = []

    def _is_clean_source(self, node):
        return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in self.clean_sources

    # --- pass 1: imports (run before calls) ---
    def collect_imports(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if _basename(node.module) in self.primitive_modules:
                    for alias in node.names:
                        if alias.name in self.tracked:
                            self.local_fn[alias.asname or alias.name] = self.tracked[alias.name]
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _basename(alias.name) in self.primitive_modules:
                        self.namespaces.add(alias.asname or alias.name)

    def _callee_role(self, func):
        if isinstance(func, ast.Name):
            return self.local_fn.get(func.id)
        if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id in self.namespaces and func.attr in self.tracked):
            return self.tracked[func.attr]
        return None

    def _is_unwrapped(self, arg):
        # Only the import-bound unwrap(x) form is unambiguous — you unwrap nothing
        # but a marked value. A bare x['value'] / x.value cannot be proven to hold a
        # marked value without dataflow (it is just as likely a raw incoming field),
        # so it is out of scope: zero false positives over catching every manual unwrap.
        return isinstance(arg, ast.Call) and self._callee_role(arg.func) == 'unwrap'

    def _report(self, node, rule, **fmt):
        self.issues.append({'line': node.lineno, 'rule': rule, 'message': MESSAGES[rule].format(**fmt)})

    def visit_Call(self, node):
        role = self._callee_role(node.func)
        if role in ('mark', 'make_meta'):
            source = _keyword(node, 'source')
            dfm = _keyword(node, 'derived_from_mock')
            # PB1 only here: a literal derived_from_mock=False on mark/make_meta is
            # the honest stored default (no upstream taint to clear), so PB2 applies
            # only to derive overrides, where it is a genuine no-op.
            if self._is_clean_source(source) and _is_const_bool(dfm, True):
                self._report(node, 'PB1', source=source.value)
            if role == 'mark' and node.args and self._is_unwrapped(node.args[0]):
                self._report(node, 'PB4')
        elif role == 'derive':
            source = _keyword(node, 'source')
            dfm = _keyword(node, 'derived_from_mock')
            if self._is_clean_source(source):
                self._report(node, 'PB3', source=source.value)
            if _is_const_bool(dfm, False):
                self._report(node, 'PB2')
        self.generic_visit(node)


class _OutputVisitor:
    """#91 — flag module-level (non-_) functions whose return is a provably-raw
    BinOp, directly or via a same-function local. Silent on anything else.
    Mirror of the JS require-provenance-output rule; see ADR-0011."""

    def __init__(self, primitive_modules, tracked):
        self.primitive_modules = primitive_modules
        self.tracked = tracked
        self.local_fn = {}       # local name -> role
        self.issues = []

    def collect_imports(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if _normalize_module_name(node.module) in self.primitive_modules:
                    for alias in node.names:
                        if alias.name in self.tracked:
                            self.local_fn[alias.asname or alias.name] = self.tracked[alias.name]

    def _is_tracked_call(self, node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and self.local_fn.get(node.func.id) is not None)

    @staticmethod
    def _is_raw(node):
        return isinstance(node, ast.BinOp)

    def _classify_locals(self, fn):
        # name -> "raw"|"tagged"; a name assigned more than once, or to anything
        # unclassifiable, is left/demoted to unknown (absent from the map). This
        # is deliberately flow-INSENSITIVE-safe: last-write-wins would over-flag an
        # early `return t` where t is still tagged before a later raw reassignment,
        # so any reassignment drops the name to unknown (silent) — errs to silence,
        # which preserves the zero-false-positive contract.
        local = {}
        seen = {}
        for stmt in fn.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                name = stmt.targets[0].id
                seen[name] = seen.get(name, 0) + 1
                if seen[name] > 1:
                    local.pop(name, None)
                    continue
                if self._is_tracked_call(stmt.value):
                    local[name] = "tagged"
                elif self._is_raw(stmt.value):
                    local[name] = "raw"
        return local

    def check_function(self, fn):
        if fn.name.startswith('_'):
            return
        local = self._classify_locals(fn)
        for node in self._returns_of(fn):
            v = node.value
            if v is None:
                continue
            if self._is_raw(v):
                self.issues.append({'line': node.lineno, 'rule': 'REQ-OUTPUT', 'message': _OUTPUT_MESSAGE})
            elif isinstance(v, ast.Name) and local.get(v.id) == "raw":
                self.issues.append({'line': node.lineno, 'rule': 'REQ-OUTPUT', 'message': _OUTPUT_MESSAGE})

    @staticmethod
    def _returns_of(fn):
        # Return nodes belonging to fn, NOT to nested functions/lambdas.
        out = []
        def walk(body):
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    continue  # nested scope — skip
                if isinstance(node, ast.Return):
                    out.append(node)
                for child in ast.iter_child_nodes(node):
                    walk([child])
        walk(fn.body)
        return out

    def visit_module(self, tree):
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.check_function(stmt)


def check(source, filename='<unknown>', clean_sources=None, extra_modules=None, extra_tracked=None):
    """Return a list of issue dicts: {'line', 'rule', 'message', 'filename'}. Empty = clean.

    clean_sources: set of source strings treated as 'clean' (defaults to CLEAN_SOURCES).
    Projects using a non-standard source vocabulary can override this per-call.

    extra_modules: extra module basenames counted as the primitive, ADDITIVE to
    PRIMITIVE_MODULES — for projects re-exporting the primitive through a wrapper
    (e.g. {'myorg_data'}). The built-in coverage cannot be configured away.

    extra_tracked: mapping of wrapper-local function name -> built-in role, for
    wrappers that rename (e.g. {'mark_value': 'mark'}). Roles must be one of
    TRACKED; an unknown role raises ValueError — a typo'd role would otherwise
    mean silently-missing coverage, the exact gap this parameter exists to close.
    """
    tracked = {n: n for n in TRACKED}
    if extra_tracked:
        bad = {name: role for name, role in extra_tracked.items() if role not in TRACKED}
        if bad:
            raise ValueError(f'extra_tracked roles must be one of {sorted(TRACKED)}; got {bad}')
        tracked.update(extra_tracked)
    modules = {_normalize_module_name(m) for m in PRIMITIVE_MODULES} | {
        _normalize_module_name(m) for m in (extra_modules or ())
    }
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as e:
        return [{'line': e.lineno or 0, 'rule': 'parse', 'message': f'syntax error: {e.msg}', 'filename': filename}]
    v = _Visitor(clean_sources=clean_sources, primitive_modules=modules, tracked=tracked)
    v.collect_imports(tree)
    v.visit(tree)
    v.issues.sort(key=lambda i: (i['line'], i['rule']))
    return [dict(i, filename=filename) for i in v.issues]


def check_outputs(source, filename='<unknown>', extra_modules=None, extra_tracked=None):
    """#91 — return a list of REQ-OUTPUT issue dicts for module-level functions
    that return an untagged raw computation. Same shape/params as check()."""
    tracked = {n: n for n in TRACKED}
    if extra_tracked:
        bad = {name: role for name, role in extra_tracked.items() if role not in TRACKED}
        if bad:
            raise ValueError(f'extra_tracked roles must be one of {sorted(TRACKED)}; got {bad}')
        tracked.update(extra_tracked)
    modules = {_normalize_module_name(m) for m in PRIMITIVE_MODULES} | {
        _normalize_module_name(m) for m in (extra_modules or ())
    }
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as e:
        return [{'line': e.lineno or 0, 'rule': 'parse', 'message': f'syntax error: {e.msg}', 'filename': filename}]
    v = _OutputVisitor(primitive_modules=modules, tracked=tracked)
    v.collect_imports(tree)
    v.visit_module(tree)
    v.issues.sort(key=lambda i: (i['line'], i['rule']))
    return [dict(i, filename=filename) for i in v.issues]


def main(argv=None):  # pragma: no cover - CLI glue; logic lives in check()/check_outputs()
    argv = sys.argv[1:] if argv is None else argv
    runner = check
    if argv and argv[0] == '--require-output':
        runner = check_outputs
        argv = argv[1:]
    total = 0
    for path in argv:
        with open(path, encoding='utf-8') as f:
            issues = runner(f.read(), path)
        for i in issues:
            total += 1
            # message already begins with the rule id (e.g. "PB1 …")
            print(f"{path}:{i['line']}: {i['message']}")
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
