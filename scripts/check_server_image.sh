#!/usr/bin/env bash
# Verify the production entry point against a fresh, disposable database.
set -euo pipefail

image=${1:?Pass the built Mimo server image}
JWT_SECRET_KEY=$(openssl rand -hex 48)
SECRET_KEY=$(python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')
export JWT_SECRET_KEY SECRET_KEY
# The optional network contains the disposable PostgreSQL service from CI.
database_args=()
if [[ -n ${2:-} ]]; then
    database_args=(--network "$2" --env DATABASE_URL=postgresql://mimo:image-check@postgres/mimo_check)
fi
container=$(docker run --detach --publish 127.0.0.1::8765 \
    --env PORT=8765 --env JWT_SECRET_KEY --env SECRET_KEY \
    "${database_args[@]}" "$image")
cleanup() {
    if [[ $? != 0 ]]; then docker logs --tail 40 "$container" >&2; fi
    docker rm --force "$container" >/dev/null
}
trap cleanup EXIT
origin="http://$(docker port "$container" 8765/tcp)"
request=(curl --noproxy '*' --fail --silent --show-error)
"${request[@]}" --retry 30 --retry-all-errors --retry-delay 1 "$origin/health" | jq -e '.status == "ok"' >/dev/null
docker exec "$container" python -c '
import os
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2

assert os.geteuid() != 0, "The service must run as an unprivileged user"
assert sqlite3.sqlite_version_info >= (3, 54, 1), "SQLite must include the 3.54 maintenance fixes"
assert ZoneInfo("Asia/Kolkata").key == "Asia/Kolkata"
libraries = Path("/proc/self/maps").read_text()
assert "/usr/lib/libpq.so." in libraries, "PostgreSQL must use the system libpq"
assert "psycopg2_binary.libs" not in libraries, "Unexpected bundled PostgreSQL libraries"
'

account=$(jq -n --arg password "$(openssl rand -hex 20)" '{email: "image-check@example.org", password: $password}')
token=$("${request[@]}" --json "$account" "$origin/auth/register" | jq -er '.access_token')
auth=(--header "Authorization: Bearer $token")
"${request[@]}" "${auth[@]}" "$origin/reports/accountability/questions" | jq -e '.questions | length > 0' >/dev/null
status=$("${request[@]}" "${auth[@]}" --request PUT --json '{"api_key":""}' \
    --output /dev/null --write-out '%{http_code}' "$origin/auth/me/gemini-key")
test "$status" = 204
echo "Production image passed startup, registration, check-in questions and account-key update."
