"""Requirement 1 timing, wider: before a remediator's first edit to its fixture
copy, list every assistant output in order (text lengths, tool names and the
file each Write targets), and flag any output that holds a plan table (a Class
column naming Mechanical and Judgment). Prints no content beyond plan rows."""
import json
import re
import sys

TASKS = "<tasks>"
name, agent = sys.argv[1], sys.argv[2]
fixture = f"/harness/fixtures/{name}/"
plan = re.compile(r"\|\s*Class\s*\|.*(mechanical.*judgment|judgment.*mechanical)", re.I | re.S)
for i, raw in enumerate(open(f"{TASKS}/{agent}.output", encoding="utf-8").read().splitlines()):
    d = json.loads(raw)
    if d.get("type") != "assistant":
        continue
    for c in d["message"].get("content", []):
        if c.get("type") == "text":
            t = c["text"]
            print(f"  {i} text {len(t)}{'  <- PLAN' if plan.search(t) else ''}")
        elif c.get("type") == "tool_use":
            inp = c.get("input", {})
            s = json.dumps(inp)
            target = inp.get("file_path") or inp.get("path") or ""
            edit = c["name"] in ("Edit", "Write", "MultiEdit") and fixture in s
            print(f"  {i} {c['name']} {target[-60:]}{'  <- PLAN' if plan.search(s) else ''}{'  <- FIRST EDIT TO FIXTURE' if edit else ''}")
            if edit:
                sys.exit(0)
