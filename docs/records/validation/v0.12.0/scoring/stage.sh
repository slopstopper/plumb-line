#!/bin/sh
# v0.12.0 harness, Part 1: stage one answer-stripped scratch copy per auditor
# (examples/AUDIT-EXPECTATIONS.md, protocol step 2): the fixture's committed
# files only (git archive), key files deleted, every line matching
# "violation" case-insensitively removed, then verified with grep -ri.
set -e
R=<repo>
S=<harness>/fixtures
rm -rf "$S"; mkdir -p "$S"
stage() { # <fixture> <variant> <name>
  d="$S/$3"; mkdir -p "$d"
  (cd "$R" && git archive --format=tar "HEAD:examples/$1/$2") | (cd "$d" && tar -xf -)
  rm -f "$d/VIOLATIONS.md" "$d/README.md"
  find "$d" -type f | while read -r f; do
    if grep -qi violation "$f"; then grep -vi violation "$f" > "$f.tmp" || true; mv "$f.tmp" "$f"; fi
  done
  if grep -rli violation "$d"; then echo "NOT CLEAN: $d"; exit 1; fi
  echo "$3: $(find "$d" -type f | wc -l | tr -d ' ') files, clean"
}
for n in 1 2; do
  stage js-payments-service broken "js-broken-$n"
  stage python-data-pipeline broken "py-broken-$n"
  stage test-honesty broken "th-broken-$n"
done
stage js-payments-service clean js-clean
stage python-data-pipeline clean py-clean
stage test-honesty clean th-clean
(cd "$R" && git rev-parse HEAD) > "$S/../base-commit"
