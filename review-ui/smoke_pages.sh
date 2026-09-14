#!/usr/bin/env bash
# HOST-SIDE render smoke test — the guard the "mrange" incident (14 Sep 2026) proved we needed.
# node --check and the static leak/door greps all PASS on a page that calls a DELETED-but-still-referenced
# function: an undefined *call* is a runtime ReferenceError, not a parse error. Only executing the page
# catches it. This headless-loads every page and fails if any logs a JS console error.
#
# Runs on the HOST (needs Chrome), not inside the container:  bash review-ui/smoke_pages.sh
set -u
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
BASE="${BASE:-http://localhost:8001}"
TMP="$(mktemp)"
PAGES="/ /dashboard /today /family /subscriptions /forecast /debt /insights /budget /zakat /wealth \
/calendar /categories /reports /goals /owed /accounts /recurring /rules /guide /settings /changelog /soon /heatmap"
fail=0
for p in $PAGES; do
  "$CHROME" --headless --disable-gpu --enable-logging=stderr --v=0 --virtual-time-budget=3000 \
    --window-size=1100,700 "$BASE$p" 2>"$TMP" >/dev/null
  err=$(grep -iE "CONSOLE.*(ReferenceError|TypeError|is not defined|Uncaught|SyntaxError)" "$TMP" \
        | grep -v cv_display_link | head -1)
  if [ -n "$err" ]; then printf '  XX %s — %s\n' "$p" "${err##*CONSOLE:}"; fail=$((fail+1)); else printf '  OK %s\n' "$p"; fi
done
rm -f "$TMP"
if [ "$fail" -eq 0 ]; then echo "PASS: every page renders with no JS console error."; exit 0
else echo "FAIL: $fail page(s) threw a runtime JS error — a page-script class node --check can't see."; exit 1; fi
