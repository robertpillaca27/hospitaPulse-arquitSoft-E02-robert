#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 backups/hospitapulse-YYYYMMDDTHHMMSSZ.dump" >&2
  exit 2
fi

BACKUP="$1"
if [ ! -f "$BACKUP" ]; then
  echo "No existe el archivo: $BACKUP" >&2
  exit 2
fi

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  echo "Define CONFIRM_RESTORE=yes para reemplazar los datos actuales." >&2
  exit 2
fi

docker compose exec -T db sh -lc \
  'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$BACKUP"
