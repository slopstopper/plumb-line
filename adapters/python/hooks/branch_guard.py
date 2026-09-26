"""branch_guard — block the first code edit on a protected branch."""
import json
import os
import re
import sys

# What counts as a blank branch: ASCII whitespace only, as in the JS twin
# (str.strip() alone would also strip Unicode spaces that JS trim() keeps).
_ASCII_WHITESPACE = " \t\n\r\f\v"

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
    unknown = branch is None or not str(branch).strip(_ASCII_WHITESPACE)
    if not unknown and branch not in protected_branches:
        return {"allow": True, "reason": "not a protected branch"}
    # No path to judge (an unmapped host payload) cannot be a docs edit.
    if not isinstance(file_path, str) or not file_path:
        return {"allow": False,
                "reason": "blocked: no file path to judge. Map the host payload's file path "
                          "into the {filePath} stdin the branch guard reads."}
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
# Every failure exits 2 (#449 review): a Claude Code hook treats only exit 2
# as a block, so a traceback's exit 1 would let the edit through.
def _main():
    raw = sys.stdin.read()
    input_data = json.loads(raw) if raw.strip() else {}
    cfg = json.loads(os.environ.get("PLUMBLINE_CFG", "{}"))
    return decide(
        file_path=input_data.get("filePath") if isinstance(input_data, dict) else None,
        branch=os.environ.get("PLUMBLINE_BRANCH"),
        protected_branches=tuple(cfg.get("protectedBranches", cfg.get("protected_branches", ["main"]))),
        docs_allowlist=tuple(cfg.get("docsAllowlist", cfg.get("docs_allowlist", []))),
    )


if __name__ == "__main__":
    try:
        r = _main()
    except Exception as e:  # noqa: BLE001 — fail closed on anything
        sys.stderr.write(f"blocked: the branch guard could not run ({e}).\n")
        sys.exit(2)
    if not r["allow"]:
        sys.stderr.write(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)
