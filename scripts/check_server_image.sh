#!/usr/bin/env bash
# Verify the production entry point against a fresh, disposable database.
set -euo pipefail

image=${1:?Pass the built Mimo server image}
JWT_SECRET_KEY=$(openssl rand -hex 48)
SECRET_KEY=$(python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')
export JWT_SECRET_KEY SECRET_KEY
container=$(docker run --detach --publish 127.0.0.1::8765 \
    --env PORT=8765 --env JWT_SECRET_KEY --env SECRET_KEY \
    --env DATABASE_URL=sqlite:////tmp/mimo-image-check.db "$image")
cleanup() {
    if [[ $? != 0 ]]; then docker logs --tail 40 "$container" >&2; fi
    docker rm --force "$container" >/dev/null
}
trap cleanup EXIT
origin="http://$(docker port "$container" 8765/tcp)"
request=(curl --noproxy '*' --fail --silent --show-error)
"${request[@]}" --retry 30 --retry-all-errors --retry-delay 1 "$origin/health" | jq -e '.status == "ok"' >/dev/null

account=$(jq -n --arg password "$(openssl rand -hex 20)" '{email: "image-check@example.org", password: $password}')
token=$("${request[@]}" --json "$account" "$origin/auth/register" | jq -er '.access_token')
auth=(--header "Authorization: Bearer $token")
"${request[@]}" "${auth[@]}" "$origin/reports/accountability/questions" | jq -e '.questions | length > 0' >/dev/null
status=$("${request[@]}" "${auth[@]}" --request PUT --json '{"api_key":""}' \
    --output /dev/null --write-out '%{http_code}' "$origin/auth/me/gemini-key")
test "$status" = 204
echo "Production image passed startup, registration, check-in questions and account-key update."
