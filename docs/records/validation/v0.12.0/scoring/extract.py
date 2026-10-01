"""Save each finished harness run's delivered message verbatim, by script (#585):
the `message` of its last SubagentHandback call (what the orchestrator
received), and beside it the text of its last end_turn message. Never retyped.

usage: python3 extract.py            # every run in runs.tsv whose transcript has ended
"""
import json
import os

H = "<harness>"
TASKS = "<tasks>"
OUT = os.path.join(H, "delivered")
os.makedirs(OUT, exist_ok=True)

for row in open(os.path.join(H, "runs.tsv"), encoding="utf-8").read().split("\n"):
    if not row.strip():
        continue
    name, agent = row.split("\t")
    path = os.path.join(TASKS, agent + ".output")
    if not os.path.exists(path):
        print(f"{name}: no transcript")
        continue
    handback, final_id, texts = None, None, {}
    for raw in open(path, encoding="utf-8").read().splitlines():
        d = json.loads(raw)
        if d.get("type") != "assistant":
            continue
        msg = d["message"]
        for c in msg.get("content", []):
            if c.get("type") == "tool_use" and c.get("name") == "SubagentHandback":
                handback = c["input"]["message"]
            elif c.get("type") == "text":
                texts.setdefault(msg["id"], []).append(c["text"])
        if msg.get("stop_reason") == "end_turn":
            final_id = msg["id"]
    if handback is None:
        print(f"{name}: not finished (no hand-back yet)")
        continue
    with open(os.path.join(OUT, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(handback)
    final = "".join(texts.get(final_id, [])) if final_id else ""
    with open(os.path.join(OUT, f"{name}.final-text.md"), "w", encoding="utf-8") as fh:
        fh.write(final)
    same = "same" if final.strip() == handback.strip() else f"differs ({len(final)} chars)"
    print(f"{name}: hand-back {len(handback)} chars; final text {same}")
