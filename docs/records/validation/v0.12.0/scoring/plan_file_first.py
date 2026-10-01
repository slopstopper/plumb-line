"""REMEDIATE-EXPECTATIONS requirement 1 as of #600: a tool call that writes the
plan table to a file outside the scratch copy must complete (a strictly
earlier assistant step) before the first tool call that changes the scratch
copy; and the final message makes no timing claim. A Bash call counts as a
change only when a segment writes inside the copy (sed -i/perl -pi, rm, mv,
tee, a redirect, cp whose destination is inside it, or a git write after cd
into it); copying out does not. Every Bash call counted is printed."""
import json
import re
import shlex
import sys

TASKS = "<tasks>"
H = "<harness>"
name, agent = sys.argv[1], sys.argv[2]
fixture = f"/harness/fixtures/{name}"
plan_re = re.compile(r"\|\s*Class\s*\|.*(mechanical.*judgment|judgment.*mechanical)", re.I | re.S)


def bash_changes_fixture(cmd):
    cwd_in = False
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        seg = seg.strip()
        if not seg:
            continue
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        if not toks:
            continue
        head = toks[0]
        if head == "cd":
            cwd_in = len(toks) > 1 and fixture in toks[1]
            continue
        redir = re.findall(r">>?\s*(\S+)", seg)
        redir = [t for t in redir if not t.startswith("&") and not t.startswith("/dev/")]
        if any(fixture in t or (cwd_in and not t.startswith("/")) for t in redir):
            return True
        if head in ("sed", "perl") and ("-i" in toks or "-pi" in toks or any(t.startswith("-i") for t in toks[1:])) \
                and (any(fixture in t for t in toks) or cwd_in):
            return True
        if head in ("rm", "mv", "tee", "touch", "mkdir", "chmod") and (any(fixture in t for t in toks[1:]) or cwd_in):
            return True
        if head == "cp" and len(toks) > 2 and (fixture in toks[-1] or (cwd_in and not toks[-1].startswith("/"))):
            return True
        if head == "git" and (cwd_in or any(fixture in t for t in toks)) and \
                any(t in ("init", "stash", "add", "commit", "checkout", "reset", "apply") for t in toks):
            return True
    return False


plan = change = None
counted = []
step, last_id = 0, None
for i, raw in enumerate(open(f"{TASKS}/{agent}.output", encoding="utf-8").read().splitlines()):
    d = json.loads(raw)
    if d.get("type") != "assistant":
        continue
    mid = d["message"].get("id")
    if mid != last_id:
        step, last_id = step + 1, mid
    for c in d["message"].get("content", []):
        if c.get("type") != "tool_use":
            continue
        inp = c.get("input", {})
        target = inp.get("file_path") or ""
        if plan is None and plan_re.search(json.dumps(inp)) and fixture not in target and c["name"] in ("Write", "Bash"):
            plan = (i, step, c["name"], target[-50:])
        if change is None:
            if c["name"] in ("Edit", "Write", "MultiEdit") and fixture in target:
                change = (i, step, c["name"], target[-50:])
            elif c["name"] == "Bash" and bash_changes_fixture(inp.get("command", "")):
                change = (i, step, "Bash", "bash")
                counted.append(inp.get("command", "")[:300])
ok = plan is not None and change is not None and plan[1] < change[1]
print(f"{name}: plan write {plan}; first change {change}; plan step before change step: {ok}")
for cmd in counted:
    print("   counted bash:", cmd)
final = open(f"{H}/delivered/{name}.md", encoding="utf-8").read()
hits = [m.group(0).strip()[:160] for m in re.finditer(
    r"(?i)[^\n]{0,70}(before (the|any) (first )?edit|printed before|written before|made before|was printed|was written)[^\n]{0,50}", final)]
print(f"   timing phrases in final message: {hits or 'none'}")
