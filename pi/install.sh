#!/usr/bin/env bash
# Instalare pe Raspberry Pi OS Lite (64-bit). Ruleaza ca utilizator normal, cu sudo.
#   git clone https://github.com/TeoChirileanu/tuya.git /opt/tuya
#   cd /opt/tuya && ./pi/install.sh
# Inainte: copiaza devices.json si tinytuya.json in /opt/tuya/config (NU sunt in git).
set -euo pipefail

USER_NAME="$(id -un)"
cd "$(dirname "$0")/.."
REPO="$(pwd)"

echo "== 1. pachete =="
sudo apt-get update -qq
sudo apt-get install -y python3-pip git

echo "== 2. tinytuya =="
pip3 install --break-system-packages --quiet tinytuya

echo "== 2b. log2ram (tine /var/log in RAM — menajeaza cardul SD) =="
if ! dpkg -s log2ram >/dev/null 2>&1; then
    echo "deb [signed-by=/etc/apt/keyrings/azlux.gpg] http://packages.azlux.fr/debian/ stable main" \
        | sudo tee /etc/apt/sources.list.d/azlux.list >/dev/null
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://azlux.fr/repo.gpg | sudo tee /etc/apt/keyrings/azlux.gpg >/dev/null
    sudo apt-get update -qq && sudo apt-get install -y log2ram || \
        echo "log2ram esuat — nu e critic, continui"
fi

echo "== 3. verificare config =="
for f in config/devices.json config/tinytuya.json; do
    [[ -f "$REPO/$f" ]] || { echo "LIPSA $REPO/$f — copiaza-l manual"; exit 1; }
done
chmod 600 "$REPO"/config/devices.json "$REPO"/config/tinytuya.json

echo "== 4. servicii systemd =="
chmod +x "$REPO"/pi/*.sh
for unit in tuya-monitor tuya-paznic tuya-publish; do
    sed "s/%i/$USER_NAME/g" "$REPO/pi/$unit.service" | sudo tee "/etc/systemd/system/$unit.service" >/dev/null
done
sudo cp "$REPO/pi/tuya-publish.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tuya-monitor tuya-paznic
sudo systemctl enable --now tuya-publish.timer

echo "== 5. stare =="
sleep 5
systemctl --no-pager --lines=3 status tuya-monitor tuya-paznic || true

cat <<'EOF'

Gata. Comenzi utile:
  journalctl -u tuya-monitor -f        # log live monitor
  journalctl -u tuya-paznic -f         # log live paznic
  systemctl restart tuya-monitor       # repornire
  tail -f /opt/tuya/data/contor_$(date +%Y%m%d).csv

Pentru publicare automata pe GitHub trebuie o deploy key cu drept de write:
  ssh-keygen -t ed25519 -C "pi-chiril" -f ~/.ssh/id_ed25519 -N ""
  cat ~/.ssh/id_ed25519.pub    # -> GitHub repo -> Settings -> Deploy keys -> Allow write
  git remote set-url origin git@github.com:TeoChirileanu/tuya.git
EOF
