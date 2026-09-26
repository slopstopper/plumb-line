"""
Every JS fixture source must load under Node (#447).

ESLint parses fixture sources as modules whatever their package says, so a
package.json that declares CommonJS over ESM sources passes the boundary and
provenance lints while `node` cannot load a single file. Remediators then have
to smoke-load a patched copy to check their edits. This test imports each
source for real, the way a user of the fixture would.

It skips without `node`; CI's examples step fails on that skip (ADR-0016).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent
SOURCES = sorted(p for p in EXAMPLES.glob("*/*/src/**/*.js") if "node_modules" not in p.parts)
TREES = sorted(p.parent for p in EXAMPLES.glob("*/*/package.json"))


def test_every_js_fixture_tree_has_its_sources_found():
    # The load check reads `<fixture>/<tree>/src/**/*.js`. A JS fixture laid out
    # any other way would otherwise go unchecked without a word.
    found = {p.relative_to(EXAMPLES).parts[:2] for p in SOURCES}
    trees = [t.relative_to(EXAMPLES).parts for t in TREES]
    assert {"js-payments-service", "ratchet-adoption-js"} <= {t[0] for t in trees}, trees
    missing = ["/".join(t) for t in trees if t not in found]
    assert not missing, f"JS fixture trees with no src/**/*.js for the load check: {missing}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("source", SOURCES, ids=lambda p: str(p.relative_to(EXAMPLES)))
def test_fixture_source_loads_under_node(source):
    result = subprocess.run(
        ["node", "--input-type=module", "-e", f"await import({source.as_uri()!r})"],
        capture_output=True, text=True, timeout=60,
    )
    errors = [line for line in result.stderr.splitlines() if "Error" in line]
    assert result.returncode == 0, errors[:1] or result.stderr
