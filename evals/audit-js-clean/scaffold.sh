#!/bin/bash
# Stage the js-payments-service/clean fixture per examples/AUDIT-EXPECTATIONS.md
# protocol step 2: copy it, delete the answer keys, strip every line naming a
# violation (case-insensitively), and verify the strip before dispatch.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="$here/../../examples/js-payments-service/clean"
dest="./fixture"
mkdir -p "$dest"
cp -R "$src/." "$dest/"
rm -f "$dest/VIOLATIONS.md" "$dest/README.md"
find "$dest" -type f -print0 | while IFS= read -r -d '' f; do
  grep -vi 'violation' "$f" > "$f.strip" || true
  mv "$f.strip" "$f"
done
if grep -ri 'violation' "$dest" > /dev/null 2>&1; then
  echo "scaffold: answer-key strings survived the strip" >&2
  exit 1
fi
