#!/bin/bash
# Stage the js-payments-service/clean fixture per examples/AUDIT-EXPECTATIONS.md
# protocol step 2: copy it, delete the answer keys, strip every line naming a
# violation (case-insensitively), and verify the strip before dispatch. Only
# the fixture's committed files are copied: an untracked node_modules or cache
# is not the fixture, and stripping it broke the js fixture's ESLint in the
# 2026-09-30 run (#530). The files are taken from the commit (git archive),
# so a run audits the fixture the record names, and an untracked fixture fails
# loudly instead of staging nothing.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="$here/../../examples/js-payments-service/clean"
dest="./fixture"
mkdir -p "$dest"
top="$(cd "$src" && git rev-parse --show-toplevel)"
prefix="$(cd "$src" && git rev-parse --show-prefix)"
(cd "$top" && git archive --format=tar "HEAD:$prefix") | (cd "$dest" && tar -xf -)
if [ -z "$(find "$dest" -type f -print -quit)" ]; then
  echo "scaffold: no committed fixture files staged from $src" >&2
  exit 1
fi
rm -f "$dest/VIOLATIONS.md" "$dest/README.md"
find "$dest" -type f -print0 | while IFS= read -r -d '' f; do
  grep -vi 'violation' "$f" > "$f.strip" || true
  mv "$f.strip" "$f"
done
if grep -ri 'violation' "$dest" > /dev/null 2>&1; then
  echo "scaffold: answer-key strings survived the strip" >&2
  exit 1
fi
