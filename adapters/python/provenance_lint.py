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

def _basename(module):
    return (module or '').split('.')[-1]


def _keyword(call, name):
    """The value node of keyword `name` on a call, or None (ignores **kwargs)."""
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_clean_source(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in CLEAN_SOURCES


def _is_const_bool(node, value):
    return isinstance(node, ast.Constant) and node.value is value


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        self.local_fn = {}      # local name -> tracked role
        self.namespaces = set()  # locals bound to a primitive module
        self.issues = []

    # --- pass 1: imports (run before calls) ---
    def collect_imports(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if _basename(node.module) in PRIMITIVE_MODULES:
                    for alias in node.names:
                        if alias.name in TRACKED:
                            self.local_fn[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _basename(alias.name) in PRIMITIVE_MODULES:
                        self.namespaces.add(alias.asname or alias.name)

    def _callee_role(self, func):
        if isinstance(func, ast.Name):
            return self.local_fn.get(func.id)
        if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id in self.namespaces and func.attr in TRACKED):
            return func.attr
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
            if _is_clean_source(source) and _is_const_bool(dfm, True):
                self._report(node, 'PB1', source=source.value)
            if role == 'mark' and node.args and self._is_unwrapped(node.args[0]):
                self._report(node, 'PB4')
        elif role == 'derive':
            source = _keyword(node, 'source')
            dfm = _keyword(node, 'derived_from_mock')
            if _is_clean_source(source):
                self._report(node, 'PB3', source=source.value)
            if _is_const_bool(dfm, False):
                self._report(node, 'PB2')
        self.generic_visit(node)


def check(source, filename='<unknown>'):
    """Return a list of issue dicts: {'line', 'rule', 'message'}. Empty = clean."""
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as e:
        return [{'line': e.lineno or 0, 'rule': 'parse', 'message': f'syntax error: {e.msg}'}]
    v = _Visitor()
    v.collect_imports(tree)
    v.visit(tree)
    v.issues.sort(key=lambda i: (i['line'], i['rule']))
    return v.issues


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    total = 0
    for path in argv:
        with open(path, encoding='utf-8') as f:
            issues = check(f.read(), path)
        for i in issues:
            total += 1
            # message already begins with the rule id (e.g. "PB1 …")
            print(f"{path}:{i['line']}: {i['message']}")
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
