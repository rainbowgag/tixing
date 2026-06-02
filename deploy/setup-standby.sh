#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rainbowgag/tixing.git"
RAW_BASE="https://raw.githubusercontent.com/rainbowgag/tixing/main"
DOMAIN="t.yaml.uk"
HTTP_PORT="25531"
EMAIL=""
ADMIN_USER="admin"
ADMIN_PASSWORD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2 ;;
    --raw-base) RAW_BASE="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --port) HTTP_PORT="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --admin-user) ADMIN_USER="$2"; shift 2 ;;
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$EMAIL" || -z "$ADMIN_PASSWORD" ]]; then
  echo "Usage: sudo bash setup-standby.sh --email admin@example.com --admin-password 'strong-password'"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run as root with sudo"
  exit 1
fi

curl -fsSL "${RAW_BASE}/deploy/install.sh" | bash -s -- \
  --repo "${REPO_URL}" \
  --domain "${DOMAIN}" \
  --port "${HTTP_PORT}" \
  --no-cert \
  --email "${EMAIL}" \
  --admin-user "${ADMIN_USER}" \
  --admin-password "${ADMIN_PASSWORD}"

systemctl disable --now line-crm-reminder.timer >/dev/null 2>&1 || true
systemctl disable --now line-crm-backup.timer >/dev/null 2>&1 || true
touch /opt/line-crm/STANDBY_MODE
chown linecrm:linecrm /opt/line-crm/STANDBY_MODE

echo "Standby installed at http://${DOMAIN}:${HTTP_PORT}"
echo "Reminder and backup timers are disabled on this standby node."
