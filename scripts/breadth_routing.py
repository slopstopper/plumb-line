#!/usr/bin/env python3
"""breadth_routing — which skill won each probe of a breadth run (#487).

A breadth query set (evals/trigger/breadth-queries.json) names, per query,
the skill that should win (`expected_skill`; null for a near-miss that
should trigger no plumb-line skill). scripts/trigger_check.py measures one
target skill per run, but records the winner of every probe, so one run
over the set shows routing across all the skills. This reads that record.

A query is routed as expected when its skill wins at least half its probes
(the trigger threshold trigger_check uses by default); a near-miss only
when no probe triggers any skill.

Usage (from repo root):

    # the eval set trigger_check reads, for one target skill
    python3 scripts/breadth_routing.py --derive plumb-line-method \\
        evals/trigger/breadth-queries.json > breadth-method.json
    python3 scripts/trigger_check.py breadth-method.json plumb-line-method \\
        RECORD.json --plugin-dir . --screen-model claude-opus-5-5 --screen-runs 2
    # the routing across all five skills
    python3 scripts/breadth_routing.py evals/trigger/breadth-queries.json RECORD.json
"""
import json
import sys


def derive(queries_path, target):
    """The breadth set as trigger_check's eval set for one target skill."""
    with open(queries_path, encoding="utf-8") as f:
        queries = json.load(f)
    return [{"query": q["query"], "should_trigger": q["expected_skill"] == target}
            for q in queries]


def route(queries_path, record_path):
    """(rows, by_skill): per query {query, expected, winners, routed}, and per
    expected skill (routed, total). A query absent from the record raises
    KeyError: the record is not a run over this set."""
    with open(queries_path, encoding="utf-8") as f:
        queries = json.load(f)
    with open(record_path, encoding="utf-8") as f:
        record = json.load(f)
    by_query = {r["query"]: r for r in record["results"]}
    rows, by_skill = [], {}
    for q in queries:
        winners = [(w or "").split(":")[-1] or None for w in by_query[q["query"]]["winners"]]
        if not winners:
            raise ValueError(f"no probes recorded for {q['query'][:60]!r}")
        expected = q["expected_skill"]
        if expected is None:
            routed = all(w is None for w in winners)
        else:
            routed = 2 * sum(1 for w in winners if w == expected) >= len(winners)
        rows.append({"query": q["query"], "expected": expected, "winners": winners,
                     "routed": routed})
        key = expected or "none"
        done, total = by_skill.get(key, (0, 0))
        by_skill[key] = (done + routed, total + 1)
    return rows, by_skill


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 3 and argv[0] == "--derive":
        print(json.dumps(derive(argv[2], argv[1]), indent=1, ensure_ascii=False))
        return 0
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    rows, by_skill = route(*argv)
    for n, row in enumerate(rows, start=1):
        print(f"{n:>2} {'ok  ' if row['routed'] else 'MISS'} "
              f"expected={row['expected'] or 'none':<22} "
              f"winners={[w or '-' for w in row['winners']]}")
    print(f"\n{sum(r['routed'] for r in rows)}/{len(rows)} routed as expected")
    for skill, (done, total) in by_skill.items():
        print(f"  {skill}: {done}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
