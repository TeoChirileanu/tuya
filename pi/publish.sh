#!/usr/bin/env bash
# Regenereaza docs/index.html din CSV-urile locale si publica pe GitHub Pages.
# Rulat de tuya-publish.timer (din ora in ora).
set -euo pipefail
cd /opt/tuya

python3 gen_pagina.py

if [[ -n "$(git status --porcelain docs)" ]]; then
    git add docs
    git commit -m "Actualizare automata probe $(date +%d.%m.%Y\ %H:%M)"
    git push
    echo "publicat"
else
    echo "nimic nou de publicat"
fi
