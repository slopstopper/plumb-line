"""case_table_guards — the three case-table guards for the conformance tables
read by the ordinary test runners (#441): http-cases.json and
baseline-cases.json. They are the checks test_conformance.py applies to
cases.json (#369, #433): a field, a case kind or a table version the runner does
not interpret is reported, never ignored. JS twin:
primitives/conformance/table-guards.mjs."""
import json


def table_problems(table, model):
    """One message per problem; [] when the runner interprets everything.

    `model` is {'versions': [...], 'meta': [...], 'fields': {kind: [field, ...]}}:
    the table versions the runner models, the top-level keys that are metadata
    rather than case kinds, and every field the runner reads per case kind.
    """
    problems = []
    if table.get('version') not in model['versions']:
        problems.append(f"unknown case-table version {json.dumps(table.get('version'))}: "
                        f"this runner models {', '.join(map(str, model['versions']))}")
    for kind, cases in table.items():
        if kind in model['meta']:
            continue
        if kind not in model['fields']:
            problems.append(f'unknown case kind {kind}: teach this runner to interpret it')
            continue
        for c in cases:
            extra = [k for k in c if k not in model['fields'][kind]]
            if extra:
                name = json.dumps(c.get('name'), ensure_ascii=False)
                problems.append(f"{kind} case {name}: unknown field(s) {', '.join(extra)}: "
                                f"teach this runner to interpret them")
    return problems
