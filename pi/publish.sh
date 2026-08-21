#!/usr/bin/env bash
# Regenereaza docs/index.html din CSV-urile din data/ si publica pe GitHub Pages.
# Rulat de tuya-publish.timer (din ora in ora).
set -euo pipefail
cd /opt/tuya
mkdir -p logs data

# sanatatea placii: 0x0 = OK; bitii 0/16 = subtensiune (sursa slaba),
# bitii 1/17 = throttling termic. Se vede in logs/health.log prin SSH.
if command -v vcgencmd >/dev/null 2>&1; then
    printf '%s throttled=%s temp=%s\n' \
        "$(date -Is)" "$(vcgencmd get_throttled)" "$(vcgencmd measure_temp)" \
        >> logs/health.log
    tail -n 500 logs/health.log > logs/health.log.tmp && mv logs/health.log.tmp logs/health.log
fi

python3 src/gen_pagina.py

if [[ -n "$(git status --porcelain docs)" ]]; then
    git add docs
    git commit -m "Actualizare automata probe $(date +%d.%m.%Y\ %H:%M)"
    # pull inainte de push: commiturile facute de pe laptop ar respinge push-ul
    if git pull --rebase && git push; then
        printf '%s OK publicat\n' "$(date -Is)" >> logs/publish.log
        echo "publicat"
    else
        printf '%s EROARE: git pull --rebase / git push a esuat\n' "$(date -Is)" >> logs/publish.log
        echo "push esuat — vezi logs/publish.log si git status in /opt/tuya" >&2
        exit 1
    fi
else
    echo "nimic nou de publicat"
fi
