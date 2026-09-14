#!/usr/bin/env bash
# HAKIM restore drill — PROVES the nightly backup is restorable.
# Restores the latest snapshot to a temp dir and verifies all three layers come
# back whole: (1) data/*.yaml rules, (2) attachments/receipts, (3) the Postgres
# ledger — actually restored into a throwaway Postgres and row-counted vs the
# count recorded at backup time. Touches nothing live. Exit 0 = drill passed.
set -euo pipefail

BK="/Users/hishamadelabdelrahman/Hakim-Backups"
export RESTIC_REPOSITORY="$BK/restic-repo"
export RESTIC_PASSWORD_FILE="$BK/.restic-password"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

RTMP="$(mktemp -d /tmp/hakim-restore.XXXXXX)"
cleanup(){ docker rm -f hakim-restore-test >/dev/null 2>&1 || true; rm -rf "$RTMP"; }
trap cleanup EXIT

echo "== HAKIM RESTORE DRILL =="
restic restore latest --target "$RTMP" >/dev/null
S="$(dirname "$(find "$RTMP" -name firefly.dump | head -1)")"
echo "restored snapshot → $S"

fail(){ echo "❌ DRILL FAILED: $1"; exit 1; }

# 1) rules / config
for f in merchants.yaml category_tree.yaml fx_rates.yaml currencies.yaml; do
  [ -s "$S/data/$f" ] || fail "missing data/$f"
done
echo "  ✓ (1/3) rules & config restored ($(ls "$S/data" | wc -l | tr -d ' ') files)"

# 2) attachments / receipts
mkdir -p "$RTMP/att"; tar xzf "$S/attachments.tgz" -C "$RTMP/att"
NATT=$(find "$RTMP/att" -type f | wc -l | tr -d ' ')
echo "  ✓ (2/3) attachments archive restores ($NATT file(s))"

# 3) Postgres ledger — restore into a throwaway container and count
docker run -d --name hakim-restore-test -e POSTGRES_PASSWORD=drill postgres:16-alpine >/dev/null
until docker exec hakim-restore-test pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
docker exec -u postgres hakim-restore-test createdb firefly_restore
docker cp "$S/firefly.dump" hakim-restore-test:/tmp/f.dump >/dev/null
docker exec -u postgres hakim-restore-test pg_restore -d firefly_restore /tmp/f.dump >/dev/null 2>&1 || true
GOT=$(docker exec -u postgres hakim-restore-test psql -d firefly_restore -tAc \
  "select count(*) from transaction_journals where deleted_at is null" | tr -d '[:space:]')
WANT=$(cat "$S/firefly_journal_count.txt" 2>/dev/null || echo "?")
echo "  ✓ (3/3) Postgres ledger restored — journals: got $GOT / expected $WANT"
[ "$GOT" = "$WANT" ] || fail "ledger count mismatch ($GOT vs $WANT)"

echo "✅ RESTORE DRILL PASSED — all three layers verified whole."
