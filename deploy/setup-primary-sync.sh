#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/line-crm"
SSH_KEY="/root/.ssh/linecrm_replicas"
INTERVAL_MINUTES="30"
SNAPSHOT_KEEP="6"
REPLICAS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir) APP_DIR="$2"; shift 2 ;;
    --key) SSH_KEY="$2"; shift 2 ;;
    --interval) INTERVAL_MINUTES="$2"; shift 2 ;;
    --keep) SNAPSHOT_KEEP="$2"; shift 2 ;;
    --replicas) REPLICAS="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$REPLICAS" ]]; then
  echo "Usage: sudo bash setup-primary-sync.sh --replicas 'root@1.1.1.1,root@2.2.2.2,root@3.3.3.3' --interval 30 --keep 6"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run as root with sudo"
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-client rsync sqlite3

mkdir -p "$(dirname "$SSH_KEY")"
if [[ ! -f "$SSH_KEY" ]]; then
  ssh-keygen -t ed25519 -N "" -f "$SSH_KEY" -C "linecrm-replica-sync"
fi
chmod 600 "$SSH_KEY"

IFS=',' read -r -a REPLICA_ARRAY <<< "$REPLICAS"

echo "Copying SSH key to standby servers. Enter each standby root password if prompted."
for replica in "${REPLICA_ARRAY[@]}"; do
  replica="$(echo "$replica" | xargs)"
  [[ -z "$replica" ]] && continue
  ssh-copy-id -i "${SSH_KEY}.pub" "$replica" || {
    echo "Failed to copy SSH key to ${replica}."
    echo "Public key:"
    cat "${SSH_KEY}.pub"
    exit 1
  }
done

cat > /etc/linecrm-replicas.conf <<EOF
APP_DIR="${APP_DIR}"
SSH_KEY="${SSH_KEY}"
SNAPSHOT_KEEP="${SNAPSHOT_KEEP}"
REPLICAS="${REPLICAS}"
EOF
chmod 600 /etc/linecrm-replicas.conf

cat > /usr/local/sbin/linecrm-sync-replicas.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

source /etc/linecrm-replicas.conf

DB_PATH="${APP_DIR}/data/app.db"
ENV_PATH="${APP_DIR}/.env"
SNAPSHOT_DIR="${APP_DIR}/replica-snapshots"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
SNAPSHOT="${SNAPSHOT_DIR}/app-${TIMESTAMP}.db"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Database not found: ${DB_PATH}"
  exit 1
fi

mkdir -p "$SNAPSHOT_DIR"
sqlite3 "$DB_PATH" ".backup '${SNAPSHOT}'"
chmod 600 "$SNAPSHOT"

find "$SNAPSHOT_DIR" -maxdepth 1 -type f -name 'app-*.db' -printf '%T@ %p\n' \
  | sort -rn \
  | awk "NR>${SNAPSHOT_KEEP} {print \$2}" \
  | xargs -r rm -f

IFS=',' read -r -a REPLICA_ARRAY <<< "$REPLICAS"
for replica in "${REPLICA_ARRAY[@]}"; do
  replica="$(echo "$replica" | xargs)"
  [[ -z "$replica" ]] && continue
  echo "Syncing to ${replica}"
  ssh -i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$replica" \
    "mkdir -p '${APP_DIR}/data' && systemctl stop line-crm >/dev/null 2>&1 || true"
  rsync -az -e "ssh -i ${SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
    "$SNAPSHOT" "${replica}:${APP_DIR}/data/app.db.replica"
  if [[ -f "$ENV_PATH" ]]; then
    rsync -az -e "ssh -i ${SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
      "$ENV_PATH" "${replica}:${APP_DIR}/.env.replica"
  fi
  ssh -i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$replica" "
    mv '${APP_DIR}/data/app.db.replica' '${APP_DIR}/data/app.db'
    if [ -f '${APP_DIR}/.env.replica' ]; then mv '${APP_DIR}/.env.replica' '${APP_DIR}/.env'; fi
    chown -R linecrm:linecrm '${APP_DIR}/data' '${APP_DIR}/.env' 2>/dev/null || true
    chmod 640 '${APP_DIR}/data/app.db' 2>/dev/null || true
    chmod 600 '${APP_DIR}/.env' 2>/dev/null || true
    systemctl start line-crm
    systemctl disable --now line-crm-reminder.timer >/dev/null 2>&1 || true
    systemctl disable --now line-crm-backup.timer >/dev/null 2>&1 || true
  "
done

echo "Replica sync completed: ${TIMESTAMP}"
EOF
chmod 700 /usr/local/sbin/linecrm-sync-replicas.sh

cat > /etc/systemd/system/linecrm-sync-replicas.service <<EOF
[Unit]
Description=Sync Line CRM SQLite snapshot to standby VPS nodes
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/linecrm-sync-replicas.sh
EOF

cat > /etc/systemd/system/linecrm-sync-replicas.timer <<EOF
[Unit]
Description=Run Line CRM standby sync every ${INTERVAL_MINUTES} minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=${INTERVAL_MINUTES}min
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now linecrm-sync-replicas.timer
/usr/local/sbin/linecrm-sync-replicas.sh

echo "Primary sync installed."
echo "Timer: linecrm-sync-replicas.timer"
echo "Manual sync: sudo /usr/local/sbin/linecrm-sync-replicas.sh"
