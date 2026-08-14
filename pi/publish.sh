#!/usr/bin/env bash
# Regenereaza docs/index.html din CSV-urile locale si publica pe GitHub Pages.
# Rulat de tuya-publish.timer (din ora in ora).
set -euo pipefail
cd /opt/tuya

# sanatatea placii: 0x0 = OK; bitii 0/16 = subtensiune (sursa slaba),
# bitii 1/17 = throttling termic. Se vede in health.log prin SSH.
if command -v vcgencmd >/dev/null 2>&1; then
    printf '%s throttled=%s temp=%s\n' \
        "$(date -Is)" "$(vcgencmd get_throttled)" "$(vcgencmd measure_temp)" \
        >> health.log
    tail -n 500 health.log > health.log.tmp && mv health.log.tmp health.log
fi

python3 gen_pagina.py

if [[ -n "$(git status --porcelain docs)" ]]; then
    git add docs
    git commit -m "Actualizare automata probe $(date +%d.%m.%Y\ %H:%M)"
    git push
    echo "publicat"
else
    echo "nimic nou de publicat"
fi
