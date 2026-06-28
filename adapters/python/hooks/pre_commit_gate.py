"""pre_commit_gate — block a commit if any runner fails."""
def decide(runners):
    for name, fn in runners:
        if not fn():
            return {"allow": False, "reason": f"pre-commit blocked: {name} failed"}
    return {"allow": True, "reason": "all gates passed"}
