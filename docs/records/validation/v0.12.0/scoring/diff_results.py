"""For each `diff` tool call a remediator made, whether its returned output
contains a hunk (@@ ... @@), and which fixture file it covered. Also counts
diff fences in the delivered (hand-back) message."""
import json
import re
import sys

TASKS = "<tasks>"
name, agent = sys.argv[1], sys.argv[2]
lines = [json.loads(r) for r in open(f"{TASKS}/{agent}.output", encoding="utf-8").read().splitlines()]
calls = {}
for d in lines:
    if d.get("type") == "assistant":
        for c in d["message"].get("content", []):
            if c.get("type") == "tool_use" and c["name"] == "Bash" and re.search(r"\bdiff -u\b", c["input"].get("command", "")):
                f = re.findall(r"src/[\w/]+\.js", c["input"]["command"])
                calls[c["id"]] = f[-1] if f else "?"
    if d.get("type") == "user":
        content = d["message"].get("content")
        if isinstance(content, list):
            for c in content:
                if c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                    out = c.get("content")
                    text = out if isinstance(out, str) else json.dumps(out)
                    print(f"  diff of {calls[c['tool_use_id']]}: hunks {text.count('@@') // 2}")
for d in lines:
    if d.get("type") == "assistant":
        for c in d["message"].get("content", []):
            if c.get("type") == "tool_use" and c["name"] == "SubagentHandback":
                m = c["input"]["message"]
                print(f"  hand-back: code fences with '@@' or leading -/+ code lines: {len(re.findall(r'(?m)^```(?:diff)?\n(?:[-+ @].*\n)+```', m))}")
