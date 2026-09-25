"""The ratchet-adoption READMEs' byte claims, enforced (#412).

Each README says `clean/.plumb-line/ratchet.json` is exactly what
`ratchet.py update` wrote (date pinned by hand) and that re-running it over
the unchanged tree rewrites nothing; and that `broken/`'s file is `clean/`'s
with `total` removed by hand and the reason reworded. The site-list checks in
test_fixture_integrity.py do not catch a hand edit or a change to the
writer's serialisation; these do.

The JS fixture measures with the consumer's real ESLint, so it needs `npm ci`
in examples/ratchet-adoption-js/clean. Without it the JS cases skip loudly
locally; CI installs it and fails the examples step on any skip here.

Run from the repo root: python3 -m pytest -q examples/test_ratchet_fixtures.py
"""
import json
import os
import re
import shutil
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from adapters.sarif import ratchet as RT  # noqa: E402

# (fixture dir, capability, the site broken/ leaves unpinned, module the
# measurement needs installed in clean/node_modules or None)
FIXTURES = [
    ("ratchet-adoption", "python.output", "src/pricing/fx.py::total", None),
    ("ratchet-adoption-js", "js.output", "src/pricing/fx.js::total", "eslint"),
]
IDS = [f[0] for f in FIXTURES]


def _fixture(name):
    return os.path.join(_ROOT, "examples", name)


def _committed(name, tree):
    with open(os.path.join(_fixture(name), tree, ".plumb-line", "ratchet.json"), "rb") as fh:
        return fh.read()


def _readme_because(name):
    """The --because the README's regenerate command passes — the test runs
    that exact command, so the README and the fixture cannot drift apart."""
    with open(os.path.join(_fixture(name), "README.md"), encoding="utf-8") as fh:
        found = re.findall(r'ratchet\.py update --root examples/' + re.escape(name)
                           + r'/clean\s*\\?\s*--because "([^"]+)"', fh.read())
    assert len(found) == 1, f"{name}/README.md must show exactly one regenerate command"
    return found[0]


def _copy_clean(tmp_path, name, needs):
    """Copy clean/ to the same depth under tmp_path, so the JS config's
    ../../../adapters path still resolves; link node_modules rather than copy it."""
    src = os.path.join(_fixture(name), "clean")
    if needs and not os.path.isdir(os.path.join(src, "node_modules", needs)):
        pytest.skip(f"JS fixture toolchain not installed: run npm ci in examples/{name}/clean")
    dst = tmp_path / "examples" / name / "clean"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules"))
    if needs:
        os.symlink(os.path.join(src, "node_modules"), dst / "node_modules")
    os.symlink(os.path.join(_ROOT, "adapters"), tmp_path / "adapters")
    return str(dst)


def _update(root, because, today):
    manifest = os.path.join(root, ".plumb-line", "enforcement.json")
    return RT.update(root, manifest, _ROOT, because, today=today)


@pytest.mark.parametrize("name,cap,dropped,needs", FIXTURES, ids=IDS)
def test_clean_ratchet_is_byte_identical_to_a_fresh_update(tmp_path, name, cap, dropped, needs):
    root = _copy_clean(tmp_path, name, needs)
    path = os.path.join(root, ".plumb-line", "ratchet.json")
    committed = _committed(name, "clean")
    pinned_date = json.loads(committed)["history"][0]["date"]
    os.remove(path)
    code, msg, _ = _update(root, _readme_because(name), pinned_date)
    assert code == 0, msg
    with open(path, "rb") as fh:
        assert fh.read() == committed, f"{name}/clean ratchet.json is not what update writes"


@pytest.mark.parametrize("name,cap,dropped,needs", FIXTURES, ids=IDS)
def test_rerunning_update_over_clean_rewrites_nothing(tmp_path, name, cap, dropped, needs):
    root = _copy_clean(tmp_path, name, needs)
    code, msg, _ = _update(root, "a re-run must not append history", None)
    assert (code, msg) == (0, "nothing changed")
    with open(os.path.join(root, ".plumb-line", "ratchet.json"), "rb") as fh:
        assert fh.read() == _committed(name, "clean")


@pytest.mark.parametrize("name,cap,dropped,needs", FIXTURES, ids=IDS)
def test_broken_is_clean_minus_one_site_in_the_writers_format(tmp_path, name, cap, dropped, needs):
    clean = json.loads(_committed(name, "clean"))
    broken = json.loads(_committed(name, "broken"))
    # The documented hand edit, and nothing else: `dropped` removed, the
    # reason reworded, the change line saying what update would have said.
    assert broken["sites"] == {cap: [s for s in clean["sites"][cap] if s != dropped]}
    assert len(broken["history"]) == 1
    assert broken["history"][0]["date"] == clean["history"][0]["date"]
    assert broken["history"][0]["change"] == RT.pin_change(broken["sites"])
    assert broken["history"][0]["because"] != clean["history"][0]["because"]
    assert {k: v for k, v in broken.items() if k not in ("sites", "history")} == \
        {k: v for k, v in clean.items() if k not in ("sites", "history")}
    # Byte-for-byte in the writer's own serialisation.
    out = tmp_path / "ratchet.json"
    RT.write_ratchet(str(out), broken)
    assert out.read_bytes() == _committed(name, "broken")
