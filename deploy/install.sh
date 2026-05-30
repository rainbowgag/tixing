#!/usr/bin/env bash
set -euo pipefail

APP_NAME="line-crm"
APP_DIR="/opt/${APP_NAME}"
APP_USER="linecrm"
DOMAIN="t.yaml.uk"
SERVER_NAME="t.yaml.uk"
HTTP_PORT="80"
ENABLE_CERTBOT="true"
REPO_URL=""
EMAIL=""
ADMIN_USER="admin"
ADMIN_PASSWORD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; SERVER_NAME="$2"; shift 2 ;;
    --port) HTTP_PORT="$2"; shift 2 ;;
    --no-cert) ENABLE_CERTBOT="false"; shift ;;
    --email) EMAIL="$2"; shift 2 ;;
    --admin-user) ADMIN_USER="$2"; shift 2 ;;
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$REPO_URL" || -z "$EMAIL" || -z "$ADMIN_PASSWORD" ]]; then
  echo "Usage: sudo bash install.sh --repo https://github.com/user/repo.git --domain t.yaml.uk --port 8080 --no-cert --email admin@example.com --admin-user admin --admin-password 'strong-password'"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run as root with sudo"
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/data" "$APP_DIR/backups"
SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
if [[ ! -f "$APP_DIR/.env" ]]; then
  cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=sqlite:///data/app.db
ADMIN_USERNAME=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_EMAIL=${EMAIL}
MAIL_SERVER=
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
EOF
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

cat > /etc/systemd/system/${APP_NAME}.service <<EOF
[Unit]
Description=Line CRM Gunicorn
After=network.target

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn --workers 3 --bind unix:${APP_DIR}/${APP_NAME}.sock wsgi:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/${APP_NAME}-reminder.service <<EOF
[Unit]
Description=Line CRM renewal reminders

[Service]
Type=oneshot
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/scripts/reminder.py
EOF

cat > /etc/systemd/system/${APP_NAME}-reminder.timer <<EOF
[Unit]
Description=Run Line CRM renewal reminders at 08:00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/${APP_NAME}-backup.service <<EOF
[Unit]
Description=Line CRM database backup

[Service]
Type=oneshot
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/scripts/backup.py
EOF

cat > /etc/systemd/system/${APP_NAME}-backup.timer <<EOF
[Unit]
Description=Run Line CRM database backup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/nginx/sites-available/${APP_NAME} <<EOF
server {
    listen ${HTTP_PORT};
    server_name ${SERVER_NAME};

    client_max_body_size 20m;

    location / {
        include proxy_params;
        proxy_pass http://unix:${APP_DIR}/${APP_NAME}.sock;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now ${APP_NAME}
systemctl enable --now ${APP_NAME}-reminder.timer
systemctl enable --now ${APP_NAME}-backup.timer
nginx -t
systemctl enable nginx
systemctl restart nginx

if [[ "$ENABLE_CERTBOT" == "true" && "$HTTP_PORT" == "80" ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
else
  echo "Certbot skipped. It requires port 80 for the default HTTP challenge."
fi

if [[ "$ENABLE_CERTBOT" == "true" && "$HTTP_PORT" == "80" ]]; then
  echo "Installed successfully: https://${DOMAIN}"
else
  echo "Installed successfully: http://${DOMAIN}:${HTTP_PORT}"
fi
echo "Config file: ${APP_DIR}/.env"
