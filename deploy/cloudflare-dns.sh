#!/usr/bin/env bash
set -euo pipefail

: "${CF_API_TOKEN:?Please export CF_API_TOKEN}"
: "${CF_ZONE_ID:?Please export CF_ZONE_ID}"

DOMAIN="${1:-t.yaml.uk}"
IP="${2:-38.58.59.103}"

curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"${DOMAIN}\",\"content\":\"${IP}\",\"ttl\":1,\"proxied\":false}"

echo
echo "DNS record requested: ${DOMAIN} -> ${IP}"
