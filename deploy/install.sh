#!/usr/bin/env bash
# ITSS PRO TOOL — one-shot deploy.
#
#   ./deploy/install.sh
#
# Generates a gitignored .env (random access code + signing key), creates the
# runtime data/ directory, installs the systemd unit, and starts the console.
# The final systemctl commands require sudo.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="$ROOT/.env"
SERVICE=itss-pro-tool.service
UNIT_SRC="$ROOT/deploy/$SERVICE"
UNIT_DST="/etc/systemd/system/$SERVICE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "== Generating $ENV_FILE =="
  ITSS_PASS="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  cat > "$ENV_FILE" <<EOF
ITSS_PASS=$ITSS_PASS
SECRET_KEY=$SECRET_KEY
PORT=8000
DEBUG=0
EOF
  chmod 600 "$ENV_FILE"
  echo "Access code (ITSS_PASS): $ITSS_PASS"
  echo "Keep this safe — you'll use it to log in to the web console."
else
  echo "== Using existing $ENV_FILE =="
fi

echo "== Creating runtime data dir =="
mkdir -p "$ROOT/data"

echo "== Installing systemd unit =="
sudo cp "$UNIT_SRC" "$UNIT_DST"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

echo "== Service status =="
sleep 1
sudo systemctl status --no-pager "$SERVICE" | head -n 14 || true

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "ITSS PRO TOOL is running."
echo "  http://localhost:8000   (or http://${IP:-<this-host>}:8000) on the LAN"
echo "  Logs: sudo journalctl -u $SERVICE -f"
echo "  Stop: sudo systemctl stop $SERVICE"