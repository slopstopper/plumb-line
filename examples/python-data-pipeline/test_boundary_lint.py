"""
Integration test: prove the SHIPPED import-linter boundary template
catches real violations in the Python fixture packages.

Layers (top to bottom): ui, services, engine, data
- services is above engine because the clean fixture has services importing engine.
- data is at the bottom; importing ui (the planted P2 violation) is forbidden.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

THIS_FILE = pathlib.Path(__file__).resolve()
EXAMPLES_DIR = THIS_FILE.parent          # examples/python-data-pipeline/
REPO_ROOT = EXAMPLES_DIR.parent.parent   # plumb-line/
TEMPLATE_PATH = REPO_ROOT / "adapters" / "python" / "importlinter-boundary.template.ini"

BROKEN_DIR = EXAMPLES_DIR / "broken"
CLEAN_DIR = EXAMPLES_DIR / "clean"

# ---------------------------------------------------------------------------
# Config generation — derived from the template file
# ---------------------------------------------------------------------------

# Layer order top→bottom.  services sits above engine because the fixture's
# clean/src/services/source.py imports engine (services → engine is allowed).
ROOT_PACKAGE = "src"
LAYERS_TOP_TO_BOTTOM = ["src.ui", "src.services", "src.engine", "src.data"]


def derive_config_from_template() -> str:
    """
    Read the shipped template and substitute the placeholders.

    Proves the TEMPLATE shape is correct — not a hand-authored config.
    Raises ValueError if the template is missing expected placeholders.
    """
    template_src = TEMPLATE_PATH.read_text(encoding="utf-8")

    if "{{ROOT_PACKAGE}}" not in template_src:
        raise ValueError(
            f"Template at {TEMPLATE_PATH} is missing {{{{ROOT_PACKAGE}}}} placeholder"
        )
    if "{{LAYERS_TOP_TO_BOTTOM}}" not in template_src:
        raise ValueError(
            f"Template at {TEMPLATE_PATH} is missing {{{{LAYERS_TOP_TO_BOTTOM}}}} placeholder"
        )

    # import-linter expects each layer on its own indented line under 'layers ='
    layers_block = "\n    ".join(LAYERS_TOP_TO_BOTTOM)

    filled = template_src.replace("{{ROOT_PACKAGE}}", ROOT_PACKAGE)
    filled = filled.replace("{{LAYERS_TOP_TO_BOTTOM}}", layers_block)
    return filled


def run_lint_imports(fixture_dir: pathlib.Path, config_path: pathlib.Path) -> subprocess.CompletedProcess:
    """Run lint-imports in the fixture directory with the generated config."""
    return subprocess.run(
        ["lint-imports", "--config", str(config_path)],
        cwd=str(fixture_dir),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Fixtures (pytest)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generated_config_file():
    """Write the generated config to a temp file; yield its path."""
    config_content = derive_config_from_template()
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".importlinter",
        prefix="plumbline_test_",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_content)
        tmp_path = pathlib.Path(f.name)
    yield tmp_path, config_content
    tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_template_has_expected_placeholders():
    """Sanity-check: the template file on disk is the right shape."""
    src = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "{{ROOT_PACKAGE}}" in src, f"Missing {{{{ROOT_PACKAGE}}}} in {TEMPLATE_PATH}"
    assert "{{LAYERS_TOP_TO_BOTTOM}}" in src, f"Missing {{{{LAYERS_TOP_TO_BOTTOM}}}} in {TEMPLATE_PATH}"
    assert "layers" in src, f"Template at {TEMPLATE_PATH} does not mention 'layers'"


def test_broken_fixture_fails_layers_contract(generated_config_file):
    """
    broken/src/data/schema.py imports src.ui.report — data layer importing ui.
    import-linter must exit non-zero and report this as a layers contract violation.
    """
    config_path, config_content = generated_config_file
    result = run_lint_imports(BROKEN_DIR, config_path)

    assert result.returncode != 0, (
        f"Expected lint-imports to fail on broken fixture but it exited 0.\n"
        f"Config used:\n{config_content}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "BROKEN" in combined or "broken" in combined.lower(), (
        f"Expected 'BROKEN' in lint-imports output but got:\n{combined}"
    )


def test_clean_fixture_passes_layers_contract(generated_config_file):
    """
    clean/src has no upward imports — import-linter must exit 0 (contract KEPT).
    """
    config_path, config_content = generated_config_file
    result = run_lint_imports(CLEAN_DIR, config_path)

    assert result.returncode == 0, (
        f"Expected lint-imports to pass on clean fixture but it exited {result.returncode}.\n"
        f"Config used:\n{config_content}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "KEPT" in combined, (
        f"Expected 'KEPT' in lint-imports output but got:\n{combined}"
    )
