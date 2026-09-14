#!/usr/bin/env bash
# HAKIM nightly backup — the money-critical set:
#   • PostgreSQL (firefly = ledger/notes/verified stamps; openwebui = chat)
#   • Firefly attachments (receipts) from the docker volume
#   • data/*  (rules, category tree, fx, currencies, dedupe indexes, icons)
#   • hakim-brain/ (ground-truth context)
# Encrypted + deduplicated into a local restic repo. No internet, privacy-first.
#
# ROOT-CAUSE NOTE (9 Sep 2026): this script and its logs live OUTSIDE ~/Documents, and it
# reads project data via Docker (which has Full Disk Access) rather than touching the
# TCC-protected ~/Documents directly. A launchd agent that referenced a script or log path
# inside ~/Documents died with exit 78/126 ("Operation not permitted") and NEVER ran — every
# real snapshot until now was a manual terminal run. Do NOT move this back into ~/Documents.
# Install location: ~/Hakim-Backups/backup.sh  (source of truth: repo scripts/backup.sh).
set -euo pipefail

BK="/Users/hishamadelabdelrahman/Hakim-Backups"
export RESTIC_REPOSITORY="$BK/restic-repo"
export RESTIC_PASSWORD_FILE="$BK/.restic-password"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
CTR="hakim-review-ui"                       # the container that bind-mounts ./data + ./hakim-brain
NAS_REPO="${HAKIM_NAS_REPO:-}"              # offsite target; empty until the NAS is mounted

# All project I/O goes THROUGH Docker so the host process never touches ~/Documents.
put_data(){ docker exec -i "$CTR" sh -c "cat > /app/data/$1" 2>/dev/null || true; }  # stdin → data/<file>
write_status(){ printf '{"ok":%s,"ts":"%s","note":"%s"}\n' "$1" "$(date -u +%FT%TZ)" "$2" | put_data backup_status.json; }

STAGE="$BK/.staging"                         # stable path (NOT random /tmp) → restic incremental
rm -rf "$STAGE"; mkdir -p "$STAGE"
trap 'code=$?; rm -rf "$STAGE"; [ $code -ne 0 ] && write_status false "exit $code"' EXIT

echo "[$(date '+%F %T')] HAKIM backup starting"
# The 03:15 job can fire on wake BEFORE Docker Desktop is ready — wait, do not fail.
for i in $(seq 1 30); do
  if docker info >/dev/null 2>&1 && docker exec hakim-postgres true >/dev/null 2>&1; then break; fi
  if [ "$i" -eq 30 ]; then
    echo "[$(date '+%F %T')] ABORT — Docker/postgres not ready after 5 min"
    write_status false "docker not ready"; exit 75
  fi
  echo "[$(date '+%F %T')] waiting for Docker to be ready… ($i/30)"; sleep 10
done

# 1) Postgres custom-format dumps (selective restore)
docker exec hakim-postgres pg_dump -U hakim -Fc firefly  > "$STAGE/firefly.dump"
docker exec hakim-postgres pg_dump -U hakim -Fc openwebui > "$STAGE/openwebui.dump"
# 2) Firefly attachments (receipts) — tar the upload volume read-only
docker run --rm -v hakim_fireflyupload:/src:ro -v "$STAGE:/dst" alpine \
  sh -c "cd /src && tar czf /dst/attachments.tgz ." >/dev/null
# 3) config + rules + brain — pulled via Docker (bind mounts), never a host Documents read
docker cp "$CTR:/app/data" "$STAGE/data" >/dev/null
docker cp "$CTR:/app/hakim-brain" "$STAGE/hakim-brain" >/dev/null 2>&1 || true
# 4) live journal count so the restore drill can verify wholeness
docker exec hakim-postgres psql -U hakim -d firefly -tAc \
  "select count(*) from transaction_journals where deleted_at is null" \
  | tr -d '[:space:]' > "$STAGE/firefly_journal_count.txt"

restic backup "$STAGE" --tag hakim-nightly --host hakim
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune >/dev/null

# 5) OFFSITE replication (Part D) — mirror the restic repo to the NAS when present.
# A restic repo is plain files; an rsync mirror is a valid, restorable offsite copy.
NAS_OK=false; NAS_TS=""
if [ -n "$NAS_REPO" ] && mkdir -p "$NAS_REPO" 2>/dev/null && [ -w "$NAS_REPO" ]; then
  if rsync -a --delete "$RESTIC_REPOSITORY/" "$NAS_REPO/" 2>/dev/null; then
    NAS_OK=true; NAS_TS="$(date -u +%FT%TZ)"
    echo "[$(date '+%F %T')] offsite replicate → $NAS_REPO OK"
  else
    echo "[$(date '+%F %T')] offsite replicate FAILED (NAS reachable but rsync errored)"
  fi
else
  echo "[$(date '+%F %T')] offsite: NAS not mounted/writable — repo is Mac-only (offsite pending)"
fi

# 6) MANIFEST for the app's Backups panel (Part C) — published into the mounted data/ dir.
REPO_SIZE="$(du -sh "$RESTIC_REPOSITORY" 2>/dev/null | cut -f1)"
MANIFEST_TMP="$STAGE/backup_snapshots.json"
python3 - "$MANIFEST_TMP" "$RESTIC_REPOSITORY" "$REPO_SIZE" "$NAS_REPO" "$NAS_OK" "$NAS_TS" <<'PY'
import json, sys, subprocess, os
manifest, repo, size, nas_repo, nas_ok, nas_ts = sys.argv[1:7]
try:
    snaps = json.loads(subprocess.check_output(["restic","snapshots","--json"], env=dict(os.environ)).decode() or "[]")
except Exception:
    snaps = []
rows = [{"id": s.get("short_id") or s.get("id","")[:8],
         "time": s.get("time","")[:19].replace("T"," "),
         "host": s.get("hostname",""), "tags": s.get("tags",[])} for s in snaps]
rows.sort(key=lambda r: r["time"], reverse=True)
json.dump({
  "repo": repo, "size": size, "count": len(rows),
  "retention": "keep 7 daily · 4 weekly · 6 monthly",
  "schedule": "nightly 03:15 (runs on next wake if the Mac was asleep)",
  "includes": ["Firefly DB (ledger)","Open WebUI DB","receipt attachments",
               "data/ (rules · category tree · icons · fx · indexes)","hakim-brain/"],
  "excludes": ["the running containers themselves — rebuilt from git, not backed up"],
  "nas": {"configured": bool(nas_repo), "path": nas_repo, "ok": nas_ok == "True", "ts": nas_ts},
  "snapshots": rows[:20],
}, open(manifest,"w"), indent=2)
PY
put_data backup_snapshots.json < "$MANIFEST_TMP"

write_status true "ok"
echo "[$(date '+%F %T')] HAKIM backup complete"
