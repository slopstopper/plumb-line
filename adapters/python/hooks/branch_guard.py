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
    """Collapse "." and ".." segments as the JS twin's path.posix.normalize does
    (#515): a trailing slash is kept, and a backslash is an ordinary character,
    as in git paths. os.path.normpath stripped the trailing slash and the old
    code turned backslashes into "/", so Python allowed "docs\\\\..\\\\src\\\\a.py"
    and "README.md/" where JS blocked them. Checked against Node itself in
    test_hooks.py."""
    if p == "":
        return "."
    absolute = p.startswith("/")
    parts = []
    for segment in p.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            elif not absolute:
                parts.append("..")
        else:
            parts.append(segment)
    out = "/".join(parts)
    if not out and not absolute:
        out = "."
    if out and p.endswith("/"):
        out += "/"
    return ("/" if absolute else "") + out


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


# Characters git never allows in a ref name: ASCII controls, space, ~ ^ : ? * [ \
_BAD_REF_CHARS = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]")


def _is_branch_name(name):
    """True when git would accept `name` as a branch name, by git's own rule:
    `git branch` refuses HEAD and a leading "-", then applies check-ref-format
    to refs/heads/<name> (#474). The table's rows are cross-checked against
    `git check-ref-format --branch`. JS twin: isBranchName."""
    if name == "HEAD" or name.startswith("-"):
        return False
    if _BAD_REF_CHARS.search(name) or ".." in name or "@{" in name or name.endswith("."):
        return False
    return all(c and not c.startswith(".") and not c.endswith(".lock") for c in name.split("/"))


def _is_blank(branch):
    """Unset, or ASCII whitespace only, as in the JS twin."""
    return branch is None or not str(branch).strip(_ASCII_WHITESPACE)


def _blocked(file_path, branch, unknown):
    if not unknown:
        return {"allow": False,
                "reason": f"blocked: code edit to {file_path} on protected branch {branch}. Branch first."}
    why = ("PLUMBLINE_BRANCH is unset or empty" if _is_blank(branch)
           else f"PLUMBLINE_BRANCH {json.dumps(str(branch), ensure_ascii=False)} is not a branch name")
    return {"allow": False,
            "reason": f"blocked: code edit to {file_path} with the branch unknown ({why}). "
                      "Set it to the current branch."}


def decide(file_path, branch, protected_branches=("main",), docs_allowlist=()):
    # An unknown branch (unset, or empty as on a detached HEAD) is an
    # inconclusive result, never a pass (#449): judge the edit as if the
    # branch were protected, so only an edit allowed on every branch passes.
    # A value git would not accept as a branch name, such as HEAD or "main "
    # (#474), is unknown too: it names no branch the edit could be on.
    unknown = _is_blank(branch) or not _is_branch_name(str(branch))
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
# shared JSON the JS twin reads, camelCase keys only (#469).
# Every failure exits 2 (#449 review): a Claude Code hook treats only exit 2
# as a block, so a traceback's exit 1 would let the edit through.

# The only PLUMBLINE_CFG keys, and the snake_case spellings to rename (#469).
_CFG_KEYS = ("protectedBranches", "docsAllowlist")
# PLUMBLINE_CFG is shared by the hooks (adapter-contract.md), so the boundary
# guard's keys are allowed here and left to it to validate (owner decision on
# #469). The branch guard never reads them, so allowing them cannot fail open;
# anything neither guard reads still blocks.
_BOUNDARY_KEYS = ("layers", "direction")
_CFG_RENAMES = {"protected_branches": "protectedBranches", "docs_allowlist": "docsAllowlist"}


def _reject_constant(name):
    """NaN and Infinity are not JSON, and the JS twin's JSON.parse refuses them."""
    raise ValueError(f"{name} is not JSON")


def _read_config(raw):
    """PLUMBLINE_CFG as (config, None), or (None, a reason to block) (#469).
    Unset gives the defaults; set, it must be a JSON object whose own keys are
    the camelCase ones, each an array of strings with no empty docsAllowlist
    entry, plus the boundary guard's keys, left unchecked (_BOUNDARY_KEYS).
    Anything else fails closed: an
    ignored key fell back to protecting only main, and a coerced value
    (tuple("main") is its characters) left main unprotected. Twin of
    readConfig in branch-guard.mjs."""
    if raw is None:
        return {}, None
    retry = " Set it to a JSON object, or unset it for the defaults."
    try:
        cfg = json.loads(raw, parse_constant=_reject_constant)
    except ValueError:
        return None, "blocked: PLUMBLINE_CFG is not valid JSON." + retry
    if not isinstance(cfg, dict):
        return None, "blocked: PLUMBLINE_CFG is not a JSON object." + retry
    # Sorted by UTF-16 code unit, as the JS twin's sort() orders them.
    unknown = sorted((k for k in cfg if k not in _CFG_KEYS and k not in _BOUNDARY_KEYS),
                     key=lambda k: k.encode("utf-16-be", "surrogatepass"))
    if unknown:
        # json.dumps escapes everything outside printable ASCII, as the JS
        # twin's quoteKey does, whatever stderr's encoding.
        named = [f"{json.dumps(k)} (use {json.dumps(_CFG_RENAMES[k])})" if k in _CFG_RENAMES
                 else json.dumps(k) for k in unknown]
        return None, (f"blocked: PLUMBLINE_CFG has unknown key(s) {', '.join(named)}. "
                      'The branch guard reads only "protectedBranches" and "docsAllowlist"; '
                      '"layers" and "direction" are the boundary guard\'s.')
    for key in _CFG_KEYS:
        if key in cfg and not (isinstance(cfg[key], list)
                               and all(isinstance(e, str) for e in cfg[key])):
            return None, f"blocked: PLUMBLINE_CFG {key} must be an array of strings."
    # decide() only meets an empty entry when it reaches it, so an earlier
    # match or an unprotected branch let the config through (#469 review).
    if "" in cfg.get("docsAllowlist", []):
        return None, "blocked: PLUMBLINE_CFG docsAllowlist must not contain an empty entry."
    return cfg, None


def _parse_stdin(raw):
    """Stdin JSON, or ValueError("stdin is not valid JSON"): one reason in both
    twins, since each parser's own detail differs (#471 review). NaN and
    Infinity are refused, as the JS twin's JSON.parse refuses them."""
    try:
        return json.loads(raw, parse_constant=_reject_constant)
    except ValueError:
        raise ValueError("stdin is not valid JSON") from None


def _read_stdin():
    """Stdin as strict UTF-8, whatever the locale or PYTHONIOENCODING says, as
    in the JS twin (#475). A byte-order mark is kept, as the JS twin keeps it."""
    if sys.stdin is None:  # closed stdin reads as empty, as in the JS twin
        return ""
    try:
        return sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("stdin is not valid UTF-8") from None


def _env_text(name):
    """The variable read from its bytes as UTF-8, whatever the locale says. Under
    an 8-bit locale, os.environ decodes each byte as one character, so a byte
    that is not UTF-8 looks valid and valid non-ASCII text is garbled (#501
    review). None when unset; a single U+FFFD for the whole value when it is
    not UTF-8, which _env_problem reads as a reason to block."""
    if os.supports_bytes_environ:
        raw = os.environb.get(name.encode())
    else:  # Windows: the environment is already text
        value = os.environ.get(name)
        raw = None if value is None else value.encode("utf-8", "surrogatepass")
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "\ufffd"


def _env(name):
    """The variable as the hook reads it, after _env_problem has passed it."""
    return _env_text(name)


def _env_problem(name):
    """Why an environment variable cannot be used, or None (#501). The JS twin
    only sees bytes that are not UTF-8 as U+FFFD, so U+FFFD counts as not valid
    here too. JS twin: envProblem."""
    text = _env_text(name)
    if text is not None and "\ufffd" in text:
        return (f"{name} is not valid UTF-8 (or holds U+FFFD, which invalid bytes are "
                "replaced with). Set it to UTF-8 text.")
    return None


def _main():
    raw = _read_stdin()
    # Empty means JSON whitespace only, as in the JS twin: str.strip() also
    # strips \x1c-\x1f, and JS trim() also strips a byte-order mark.
    # _parse_stdin refuses NaN and Infinity, as JSON.parse does (#503).
    input_data = _parse_stdin(raw) if raw.strip(" \t\n\r") else {}
    problem = _env_problem("PLUMBLINE_BRANCH") or _env_problem("PLUMBLINE_CFG")
    if problem:
        return {"allow": False, "reason": f"blocked: {problem}"}
    cfg, reason = _read_config(_env("PLUMBLINE_CFG"))
    if reason:
        return {"allow": False, "reason": reason}
    return decide(
        file_path=input_data.get("filePath") if isinstance(input_data, dict) else None,
        branch=_env("PLUMBLINE_BRANCH"),
        protected_branches=tuple(cfg.get("protectedBranches", ["main"])),
        docs_allowlist=tuple(cfg.get("docsAllowlist", [])),
    )


def _say(text):
    """Write a reason to stderr; with stderr closed the exit code still says it."""
    if sys.stderr is not None:
        sys.stderr.write(text)


if __name__ == "__main__":
    # Reasons are written as UTF-8, as Node writes them, whatever the locale
    # or PYTHONIOENCODING says (#471 review).
    if sys.stderr is not None:  # closed (2>&-): nothing to write to
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        r = _main()
    except Exception as e:  # noqa: BLE001 — fail closed on anything
        _say(f"blocked: the branch guard could not run ({e}).\n")
        sys.exit(2)
    if not r["allow"]:
        _say(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)
