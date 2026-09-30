#!/bin/sh
# v0.12.0 harness, Part 1b: one answer-stripped scratch copy of
# js-payments-service/broken per remediator (REMEDIATE-EXPECTATIONS.md step 1).
set -e
R=<repo>
S=<harness>/fixtures
for n in 1 2; do
  d="$S/rem-$n"; rm -rf "$d"; mkdir -p "$d"
  (cd "$R" && git archive --format=tar "HEAD:examples/js-payments-service/broken") | (cd "$d" && tar -xf -)
  rm -f "$d/VIOLATIONS.md" "$d/README.md"
  find "$d" -type f | while read -r f; do
    if grep -qi violation "$f"; then grep -vi violation "$f" > "$f.tmp" || true; mv "$f.tmp" "$f"; fi
  done
  if grep -rli violation "$d"; then echo "NOT CLEAN: $d"; exit 1; fi
  echo "rem-$n: $(find "$d" -type f | wc -l | tr -d ' ') files, clean"
done
d="$S/rem-1"
grep -n "import .*ui/" "$d/src/data/rates.js"
grep -n "^const FEE\|\* FEE" "$d/src/engine/pricing.js"
grep -n "export function submitPayment\|return {\|accepted" "$d/src/services/gateway.js"
ls "$d" "$d/config" 2>/dev/null
