#!/usr/bin/env bash
# Nightly Postgres dump, keeping the last 7.
#
# Install on the server:
#   (crontab -l 2>/dev/null; echo "0 3 * * * /opt/squatchscout/deploy/backup.sh >> /opt/squatchscout/deploy/backups/cron.log 2>&1") | crontab -
#
# Restore one:
#   gunzip -c backups/2026-09-19.sql.gz | docker compose -f docker-compose.yml \
#     --project-directory . exec -T postgres psql -U squatch squatchscout
set -euo pipefail

cd /opt/squatchscout/deploy
mkdir -p backups

stamp="$(date +%F)"
target="backups/${stamp}.sql.gz"
tmp="${target}.partial"

# Dump to a .partial name and rename only on success, so a dump that dies halfway
# (disk full, container restarting) cannot leave a truncated file that looks like a
# good backup and then gets counted as one of the seven we keep.
if ! docker compose -f docker-compose.yml --project-directory . \
        exec -T postgres pg_dump -U squatch squatchscout | gzip > "$tmp"; then
    echo "$(date -Is) backup FAILED during pg_dump" >&2
    rm -f "$tmp"
    exit 1
fi

if ! gzip -t "$tmp"; then
    echo "$(date -Is) backup FAILED integrity check" >&2
    rm -f "$tmp"
    exit 1
fi

mv -f "$tmp" "$target"
echo "$(date -Is) wrote $target ($(du -h "$target" | cut -f1))"

# Keep the 7 most recent, delete the rest.
ls -1t backups/*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm --
