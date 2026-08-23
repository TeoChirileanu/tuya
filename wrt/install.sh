#!/usr/bin/env bash
# Instalare completă pe routerul OpenWrt GL-BE6500 (192.168.1.30):
#   - monitoare cloud (Chiril + Martiniuc) ca servicii procd, cu pornire la boot
#   - publicare orară a paginilor GitHub Pages (git + cron), autonom
# Rulează din rădăcina repo-ului, de pe un calculator cu acces ssh la router:
#   ./wrt/install.sh
# Necesită: ssh root@192.168.1.30 fără parolă + config/tinytuya.json local.
# Idempotent: poate fi rerulat (actualizează fișierele și repornește serviciile).
set -euo pipefail
ROUTER="root@192.168.1.30"
cd "$(dirname "$0")/.."

echo "== 1. pachete pe router =="
ssh "$ROUTER" 'opkg update && opkg install python3-light python3-pip ca-bundle \
               git openssh-client openssh-keygen'

echo "== 2. tinytuya =="
# --no-deps: cryptography (dep. declarată) nu are wheel pentru musl/aarch64;
# tinytuya face fallback automat pe pyaes (pure python) — suficient pentru cloud.
ssh "$ROUTER" 'pip3 install --quiet --no-cache-dir --no-deps tinytuya &&
               pip3 install --quiet --no-cache-dir requests colorama pyaes'

echo "== 3. cheie deploy pentru GitHub (dacă lipsește) =="
ssh "$ROUTER" 'mkdir -p /root/.ssh && chmod 700 /root/.ssh &&
  [ -f /root/.ssh/id_ed25519 ] ||
    ssh-keygen -t ed25519 -C "wrt-gl-be6500" -f /root/.ssh/id_ed25519 -N ""
  printf "Host github.com\n  IdentityFile /root/.ssh/id_ed25519\n  StrictHostKeyChecking accept-new\n" \
    > /root/.ssh/config && chmod 600 /root/.ssh/config'
PUBKEY=$(ssh "$ROUTER" 'cat /root/.ssh/id_ed25519.pub')
echo "   cheia publică a routerului: $PUBKEY"
echo "   trebuie să fie Deploy Key cu write în repo (o singură dată):"
echo "   echo \"$PUBKEY\" | gh repo deploy-key add /dev/stdin -R TeoChirileanu/tuya --title wrt-gl-be6500 --allow-write"

echo "== 4. /opt/tuya devine clone git (ca pe Pi); config/ și data/ se păstrează =="
echo "   (monitorii se opresc pe durata migrării — câteva secunde)"
ssh "$ROUTER" '
  /etc/init.d/tuya-cloud-chiril stop 2>/dev/null
  /etc/init.d/tuya-cloud-martiniuc stop 2>/dev/null
  if [ ! -d /opt/tuya/.git ]; then
    git clone https://github.com/TeoChirileanu/tuya.git /opt/tuya.new &&
    cp -a /opt/tuya/config/. /opt/tuya.new/config/ &&
    cp -a /opt/tuya/data/. /opt/tuya.new/data/ &&
    mv /opt/tuya /opt/tuya.old && mv /opt/tuya.new /opt/tuya
  fi
  cd /opt/tuya &&
  git remote set-url origin git@github.com:TeoChirileanu/tuya.git &&
  git config user.name tuya-wrt && git config user.email tuya-wrt@localhost &&
  mkdir -p logs data'

echo "== 5. script + config + servicii =="
# scp -O: routerul are Dropbear fără sftp-server — protocolul SFTP nu merge
scp -q -O src/monitor_cloud.py "$ROUTER":/opt/tuya/src/
scp -q -O config/tinytuya.json "$ROUTER":/opt/tuya/config/
scp -q -O wrt/tuya-cloud-chiril wrt/tuya-cloud-martiniuc "$ROUTER":/etc/init.d/
ssh "$ROUTER" 'chmod 600 /opt/tuya/config/tinytuya.json && chmod +x /etc/init.d/tuya-cloud-* &&
  /etc/init.d/tuya-cloud-chiril enable && /etc/init.d/tuya-cloud-martiniuc enable &&
  /etc/init.d/tuya-cloud-chiril start && /etc/init.d/tuya-cloud-martiniuc start'

echo "== 6. seed istoric (contor_*.csv locale) + cron orar pentru publish =="
scp -q -O data/contor_*.csv "$ROUTER":/opt/tuya/data/
ssh "$ROUTER" 'grep -q "wrt/publish.sh" /etc/crontabs/root 2>/dev/null ||
    echo "7 * * * * sh /opt/tuya/wrt/publish.sh >> /opt/tuya/logs/publish-cron.log 2>&1" >> /etc/crontabs/root
  /etc/init.d/cron enable && /etc/init.d/cron restart'

echo "== 7. verificare (aștept 15s) =="
sleep 15
ssh "$ROUTER" 'ps | grep -c "[m]onitor_cloud"; ls -l /opt/tuya/data/ | tail -4; crontab -l'
