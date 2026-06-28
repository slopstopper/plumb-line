"""branch_guard — block the first code edit on a protected branch."""
def decide(file_path, branch, protected_branches=("main",), docs_allowlist=()):
    if branch not in protected_branches:
        return {"allow": True, "reason": "not a protected branch"}
    if any(file_path == p or file_path.startswith(p) for p in docs_allowlist):
        return {"allow": True, "reason": "docs edit allowed on protected branch"}
    return {"allow": False,
            "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}
