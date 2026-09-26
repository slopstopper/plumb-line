"""branch_guard — block the first code edit on a protected branch."""
import json
import os
import re
import sys

# A bare "*.ext" extension glob (no path separators).
_EXTENSION_GLOB = re.compile(r"^\*\.[A-Za-z0-9.]+$")


def _normalize_path(p):
    """Collapse . and .. segments using os.path.normpath, then replace backslashes."""
    return os.path.normpath(p).replace("\\", "/")


def _matches_allowlist_entry(normalized_candidate, entry):
    """Return True if normalized_candidate matches a single allowlist entry."""
    if entry == "":
        raise ValueError("docs_allowlist must not contain empty entries")
    if _EXTENSION_GLOB.match(entry):
        # Extension glob: "*.md" matches any file ending in ".md", at any depth.
        # The candidate is already guaranteed not to escape upward (see decide).
        return normalized_candidate.endswith(entry[1:])
    normalized_entry = _normalize_path(entry)
    if entry.endswith("/"):
        # Directory entry: candidate must equal the dir or be inside it at a segment boundary.
        dir_prefix = normalized_entry if normalized_entry.endswith("/") else normalized_entry + "/"
        return normalized_candidate == normalized_entry or normalized_candidate.startswith(dir_prefix)
    # File entry: exact match only.
    return normalized_candidate == normalized_entry


def _blocked(file_path, branch, unknown):
    if unknown:
        return {"allow": False,
                "reason": f"blocked: code edit to {file_path} with the branch unknown "
                          "(PLUMBLINE_BRANCH is unset or empty). Set it to the current branch."}
    return {"allow": False,
            "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}


def decide(file_path, branch, protected_branches=("main",), docs_allowlist=()):
    # An unknown branch (unset, or empty as on a detached HEAD) is an
    # inconclusive result, never a pass (#449): judge the edit as if the
    # branch were protected, so only an edit allowed on every branch passes.
    unknown = branch is None or not str(branch).strip()
    if not unknown and branch not in protected_branches:
        return {"allow": True, "reason": "not a protected branch"}
    # Normalize candidate first; an upward-escaping path is never a docs match.
    normalized_candidate = _normalize_path(file_path)
    if normalized_candidate.startswith(".."):
        return _blocked(file_path, branch, unknown)
    if any(_matches_allowlist_entry(normalized_candidate, entry) for entry in docs_allowlist):
        return {"allow": True, "reason": "docs edit allowed on any branch" if unknown
                else "docs edit allowed on protected branch"}
    return _blocked(file_path, branch, unknown)


# CLI, the hook I/O contract (adapter-contract.md): `{ "filePath": ... }` on
# stdin, the branch from PLUMBLINE_BRANCH, config from PLUMBLINE_CFG; exit 2 to
# block. Until 0.11.3 this module had no entry point, so wired as a hook it
# exited 0 and never blocked, while its JS twin did. PLUMBLINE_CFG is the
# shared JSON the JS twin reads (camelCase); snake_case keys are accepted too.
if __name__ == "__main__":
    raw = sys.stdin.read()
    input_data = json.loads(raw) if raw.strip() else {}
    cfg = json.loads(os.environ.get("PLUMBLINE_CFG", "{}"))
    r = decide(
        file_path=input_data.get("filePath", ""),
        branch=os.environ.get("PLUMBLINE_BRANCH"),
        protected_branches=tuple(cfg.get("protectedBranches", cfg.get("protected_branches", ["main"]))),
        docs_allowlist=tuple(cfg.get("docsAllowlist", cfg.get("docs_allowlist", []))),
    )
    if not r["allow"]:
        sys.stderr.write(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)
