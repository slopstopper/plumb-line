"""branch_guard — block the first code edit on a protected branch."""
import os


def _normalize_path(p):
    """Collapse . and .. segments using os.path.normpath, then replace backslashes."""
    return os.path.normpath(p).replace("\\", "/")


def _matches_allowlist_entry(normalized_candidate, entry):
    """Return True if normalized_candidate matches a single allowlist entry."""
    if entry == "":
        raise ValueError("docs_allowlist must not contain empty entries")
    normalized_entry = _normalize_path(entry)
    if entry.endswith("/"):
        # Directory entry: candidate must equal the dir or be inside it at a segment boundary.
        dir_prefix = normalized_entry if normalized_entry.endswith("/") else normalized_entry + "/"
        return normalized_candidate == normalized_entry or normalized_candidate.startswith(dir_prefix)
    # File entry: exact match only.
    return normalized_candidate == normalized_entry


def decide(file_path, branch, protected_branches=("main",), docs_allowlist=()):
    if branch not in protected_branches:
        return {"allow": True, "reason": "not a protected branch"}
    # Normalize candidate first; an upward-escaping path is never a docs match.
    normalized_candidate = _normalize_path(file_path)
    if normalized_candidate.startswith(".."):
        return {"allow": False,
                "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}
    if any(_matches_allowlist_entry(normalized_candidate, entry) for entry in docs_allowlist):
        return {"allow": True, "reason": "docs edit allowed on protected branch"}
    return {"allow": False,
            "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}
