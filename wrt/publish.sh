#!/bin/sh
# Regenerează docs/ (hub + chiril + martiniuc) din CSV-urile locale și publică
# pe GitHub Pages. Rulat din cron pe router (orar). Echivalentul lui pi/publish.sh.
set -eu
cd /opt/tuya
mkdir -p logs

python3 src/gen_pagina.py

if [ -n "$(git status --porcelain docs)" ]; then
    git add docs
    git commit -m "Actualizare automata probe $(date +'%d.%m.%Y %H:%M')"
    # pull înainte de push: commiturile făcute din alte părți ar respinge push-ul
    if git pull --rebase && git push; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') OK publicat" >> logs/publish.log
        echo "publicat"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') EROARE: git pull --rebase / git push a esuat" >> logs/publish.log
        echo "push esuat — vezi logs/publish.log" >&2
        exit 1
    fi
else
    echo "nimic nou de publicat"
fi
