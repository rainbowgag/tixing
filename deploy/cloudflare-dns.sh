#!/usr/bin/env bash
set -euo pipefail

: "${CF_API_TOKEN:?Please export CF_API_TOKEN}"
: "${CF_ZONE_ID:?Please export CF_ZONE_ID}"

DOMAIN="${1:-t.yaml.uk}"
IP="${2:-38.58.59.103}"

API="https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records"
AUTH_HEADER="Authorization: Bearer ${CF_API_TOKEN}"

RECORD_ID="$(curl -fsS -G "${API}" \
  -H "${AUTH_HEADER}" \
  --data-urlencode "type=A" \
  --data-urlencode "name=${DOMAIN}" | python3 -c 'import json,sys; data=json.load(sys.stdin); rows=data.get("result") or []; print(rows[0]["id"] if rows else "")')"

if [[ -n "${RECORD_ID}" ]]; then
  curl -fsS -X PUT "${API}/${RECORD_ID}" \
    -H "${AUTH_HEADER}" \
    -H "Content-Type: application/json" \
    --data "{\"type\":\"A\",\"name\":\"${DOMAIN}\",\"content\":\"${IP}\",\"ttl\":1,\"proxied\":false}"
  ACTION="updated"
else
  curl -fsS -X POST "${API}" \
    -H "${AUTH_HEADER}" \
    -H "Content-Type: application/json" \
    --data "{\"type\":\"A\",\"name\":\"${DOMAIN}\",\"content\":\"${IP}\",\"ttl\":1,\"proxied\":false}"
  ACTION="created"
fi

curl -fsS -X PATCH "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/settings/ssl" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"value":"full"}' >/dev/null || true

echo
echo "DNS record ${ACTION}: ${DOMAIN} -> ${IP}"
