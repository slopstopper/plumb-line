"""boundary_guard — block imports that violate one-way layering."""
import re
import json
import os
import sys

def _layer_of(path, layers):
    for layer in layers:
        # \Z, not $: $ also matches before a trailing newline, which the JS
        # twin's search does not (#471 re-review).
        if re.search(rf"(^|/){re.escape(layer)}(/|\Z)", path):
            return layer
    return None

# The reason for an importPath that is present but not a string (#471).
# JS twin: IMPORT_PATH_REASON.
_IMPORT_PATH_REASON = ("blocked: importPath must be a string. Map the import being added into the "
                       "{filePath, importPath} stdin the boundary guard reads, or leave it out "
                       "when there is none.")

# The reason for an import with no layers to judge it by (#516).
# JS twin: NO_LAYERS_REASON.
_NO_LAYERS_REASON = ('blocked: no layers configured, so this import cannot be judged. Set "layers" in '
                     "PLUMBLINE_CFG to the project's layer names, top to bottom.")

def decide(file_path, import_path, layers, direction="downward"):
    # No path to judge (an unmapped host payload) cannot be judged, so it
    # blocks (#471), as in the branch guard (#449 review).
    if not isinstance(file_path, str) or not file_path:
        return {"allow": False,
                "reason": "blocked: no file path to judge. Map the host payload's file path "
                          "into the {filePath, importPath} stdin the boundary guard reads."}
    # Most edits add no import: with none (or an empty one) there is nothing
    # to judge (owner decision on #471). The CLI blocks an importPath that is
    # present on stdin but null.
    if import_path is None or import_path == "":
        return {"allow": True, "reason": "no import to judge"}
    if not isinstance(import_path, str):
        return {"allow": False, "reason": _IMPORT_PATH_REASON}
    # An import to judge and no layers to judge it by is not a pass: it
    # blocks, as the gate blocks with no gates (#476) and an explicit empty
    # `layers` does (#471). Owner decision on #516. JS twin: NO_LAYERS_REASON.
    if not isinstance(layers, list) or not layers:
        return {"allow": False, "reason": _NO_LAYERS_REASON}
    src, dst = _layer_of(file_path, layers), _layer_of(import_path, layers)
    if not src or not dst or src == dst:
        return {"allow": True, "reason": "same or unscoped layer"}
    si, di = layers.index(src), layers.index(dst)
    ok = di > si if direction == "downward" else di < si
    if ok:
        return {"allow": True, "reason": f"{src} -> {dst} respects {direction}"}
    return {"allow": False, "reason": f"boundary break: {src} must not import {dst} ({direction})"}


# CLI, the hook I/O contract (adapter-contract.md): `{ "filePath": ...,
# "importPath": ... }` on stdin, config from PLUMBLINE_CFG; exit 2 to block.
# Every failure exits 2 (#471), as in the branch guard: a Claude Code hook
# treats only exit 2 as a block, so a traceback's exit 1 would let the edit
# through.

# The only PLUMBLINE_CFG keys this guard reads (#471).
_CFG_KEYS = ("layers", "direction")
# PLUMBLINE_CFG is shared by the hooks (adapter-contract.md), so the branch
# guard's keys are allowed here and left to it to validate: the mirror of the
# branch guard's rule (owner decision on #469). The boundary guard never reads
# them, so allowing them cannot fail open; anything neither guard reads still
# blocks. The snake_case spellings the branch guard renames are named with the
# key to use, as it names them.
_BRANCH_KEYS = ("protectedBranches", "docsAllowlist")
_CFG_RENAMES = {"protected_branches": "protectedBranches", "docs_allowlist": "docsAllowlist"}
_DIRECTIONS = ("downward", "upward")


def _reject_constant(name):
    """NaN and Infinity are not JSON, and the JS twin's JSON.parse refuses them."""
    raise ValueError(f"{name} is not JSON")


def _read_config(raw):
    """PLUMBLINE_CFG as (config, None), or (None, a reason to block) (#471).
    Unset gives the defaults (no layers, so an import to judge blocks, #516;
    direction downward); set, it must be a JSON object whose own keys are `layers`, a
    non-empty array of non-empty strings, and `direction`, exactly "downward"
    or "upward", plus the branch guard's keys, left unchecked (_BRANCH_KEYS).
    Anything else fails closed: an ignored `layer` typo checked no layers, and
    any direction but "downward" was read as upward. Twin of readConfig in
    boundary-guard.mjs; mirrors _read_config in branch_guard.py."""
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
    unknown = sorted((k for k in cfg if k not in _CFG_KEYS and k not in _BRANCH_KEYS),
                     key=lambda k: k.encode("utf-16-be", "surrogatepass"))
    if unknown:
        # json.dumps escapes everything outside printable ASCII, as the JS
        # twin's quoteKey does, whatever stderr's encoding.
        named = [f"{json.dumps(k)} (use {json.dumps(_CFG_RENAMES[k])})" if k in _CFG_RENAMES
                 else json.dumps(k) for k in unknown]
        return None, (f"blocked: PLUMBLINE_CFG has unknown key(s) {', '.join(named)}. "
                      'The boundary guard reads only "layers" and "direction"; '
                      '"protectedBranches" and "docsAllowlist" are the branch guard\'s.')
    if "layers" in cfg:
        layers = cfg["layers"]
        if not (isinstance(layers, list) and all(isinstance(e, str) for e in layers)):
            return None, "blocked: PLUMBLINE_CFG layers must be an array of strings."
        # An explicit empty list checks nothing, and an empty name matches
        # only paths with an empty segment: neither is a layering (#471).
        if not layers:
            return None, "blocked: PLUMBLINE_CFG layers must not be empty."
        if "" in layers:
            return None, "blocked: PLUMBLINE_CFG layers must not contain an empty entry."
    if "direction" in cfg and cfg["direction"] not in _DIRECTIONS:
        return None, 'blocked: PLUMBLINE_CFG direction must be "downward" or "upward".'
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
    in the JS twin (#471, as #475 did for the branch guard). A byte-order mark
    is kept, as the JS twin keeps it."""
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
    # strips \x1c-\x1f, and JS trim() also strips a byte-order mark. NaN and
    # Infinity are refused, as the JS twin's JSON.parse refuses them.
    parsed = _parse_stdin(raw) if raw.strip(" \t\n\r") else {}
    # Stdin that is not an object has no filePath, so decide() blocks it.
    input_data = parsed if isinstance(parsed, dict) else {}
    problem = _env_problem("PLUMBLINE_CFG")
    if problem:
        return {"allow": False, "reason": f"blocked: {problem}"}
    cfg, reason = _read_config(_env("PLUMBLINE_CFG"))
    if reason:
        return {"allow": False, "reason": reason}
    if "importPath" in input_data and not isinstance(input_data["importPath"], str):
        return {"allow": False, "reason": _IMPORT_PATH_REASON}
    return decide(
        file_path=input_data.get("filePath"),
        import_path=input_data.get("importPath"),
        layers=cfg.get("layers", []),
        direction=cfg.get("direction", "downward"),
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
        _say(f"blocked: the boundary guard could not run ({e}).\n")
        sys.exit(2)
    if not r["allow"]:
        _say(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)
