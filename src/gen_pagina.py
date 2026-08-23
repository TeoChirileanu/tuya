"""Generează paginile publice de probe pentru calitatea tensiunii (GitHub Pages).

Pentru fiecare punct de măsurare din SITES: citește CSV-urile asociate din data/,
construiește graficul V/timp pe faze (SVG inline), tabelul încălcărilor și
statisticile → docs/<punct>/index.html. La rularea completă regenerează și
hub-ul docs/index.html. Fără date personale — doar măsurători.

Afișare: max o citire la 10 minute, PLUS toate încălcările integral — altfel, cu
cadența cloud de 10 s, tabelele ar exploda. Statisticile (min/max/încălcări) se
calculează întotdeauna pe setul complet.

Utilizare:  python gen_pagina.py [chiril|martiniuc|all]   (implicit: all)
            (apoi commit + push -> GitHub Pages; pe router face asta wrt/publish.sh)
"""

import csv
import glob
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # radacina repo (scripturile stau in src/)
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")

V_LO, V_HI = 207.0, 253.0       # limite 95% (±10%)
V_ABS_LO = 195.5                # limită absolută inferioară (−15%)
Y_MIN, Y_MAX = 140, 270
W, H = 920, 420
ML, MR, MT, MB = 52, 120, 16, 40  # margini (dreapta: etichete directe)
THIN_S = 600                    # afișare: max o citire la 10 min (+ toate încălcările)

PHASES = (("L1", 1), ("L2", 4), ("L3", 7))  # nume, index coloană V în rând
COLORS = {"L1": "var(--s1)", "L2": "var(--s2)", "L3": "var(--s3)"}

LIMITS = ("limite conform Ordin ANRE 46/2021, art. 25: "
          "207–253 V (95%), absolut 195,5–253 V")

SITES = {
    "chiril": {
        "hub": "Chiril · POD EMO2233339",
        "globs": ("contor_*.csv", "cloud_log_chiril_*.csv"),
        "title": "Calitatea tensiunii de alimentare — POD EMO2233339",
        "sub": "Măsurători continue cu contor trifazat propriu, imediat în aval de "
               "punctul de delimitare · Reclamație Delgaz Grid nr. RSS_35819 / "
               f"13.08.2026 · {LIMITS}",
        "method": "contor trifazat propriu; citire locală (protocol Tuya) până la "
                  "15.08.2026, apoi prin cloud Tuya (la 10 s)",
    },
    "martiniuc": {
        "hub": "Martiniuc",
        "globs": ("cloud_log_martiniuc_*.csv",),
        "title": "Calitatea tensiunii de alimentare — Martiniuc",
        "sub": f"Măsurători continue cu contor trifazat propriu · {LIMITS}",
        "method": "contor trifazat propriu; citire prin cloud Tuya (la 10 s)",
    },
}

CSS = """
:root {
  color-scheme: light;
  --surf: #fcfcfb; --page: #f9f9f7; --ink: #0b0b0b; --ink2: #52514e;
  --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a;
  --crit: #d03b3b; --band: rgba(27,175,122,0.07);
  --ring: rgba(11,11,11,0.10);
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --surf: #1a1a19; --page: #0d0d0d; --ink: #ffffff; --ink2: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835;
    --s1: #3987e5; --s2: #d95926; --s3: #199e70;
    --crit: #d03b3b; --band: rgba(25,158,112,0.10);
    --ring: rgba(255,255,255,0.10);
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1000px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 24px; margin: 8px 0 4px; }
.sub { color: var(--ink2); margin: 0 0 20px; }
.tiles { display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 20px; }
.tile { background: var(--surf); border: 1px solid var(--ring);
  border-radius: 10px; padding: 14px 18px; flex: 1 1 180px; }
.tile .v { font-size: 28px; font-weight: 700; }
.tile .v.bad { color: var(--crit); }
.tile .l { color: var(--ink2); font-size: 13px; }
.card { background: var(--surf); border: 1px solid var(--ring);
  border-radius: 10px; padding: 16px; margin-bottom: 20px; overflow-x: auto; }
.tick { font-size: 11px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.lim { font-size: 11px; fill: var(--ink2); }
.crit-t { fill: var(--crit); }
.dlab { font-size: 12px; font-weight: 600; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--grid); }
th { color: var(--ink2); font-weight: 600; font-size: 13px; }
th[data-s] { cursor: pointer; user-select: none; white-space: nowrap; }
th[data-s]::after { content: " ⇅"; color: var(--muted); font-size: 11px; }
th[data-s][data-dir="asc"]::after { content: " ▲"; color: var(--ink); }
th[data-s][data-dir="desc"]::after { content: " ▼"; color: var(--ink); }
td.bad { color: var(--crit); font-weight: 700; }
.note { color: var(--ink2); font-size: 13px; }
a { color: var(--s1); }
a.hub { display: block; text-decoration: none; color: var(--ink);
  background: var(--surf); border: 1px solid var(--ring); border-radius: 10px;
  padding: 16px 18px; margin-bottom: 12px; }
a.hub:hover { border-color: var(--s1); }
.hubt { font-size: 18px; font-weight: 700; }
"""

JS = """
(function () {
  var reg = document.querySelector('#registru tbody');
  document.getElementById('doarBad').addEventListener('change', function () {
    var only = this.checked;
    reg.querySelectorAll('tr').forEach(function (tr) {
      tr.style.display = (!only || tr.dataset.bad === '1') ? '' : 'none';
    });
  });
  // sortare pe orice tabel .sortable: direcție per coloană + săgeată vizibilă
  document.querySelectorAll('table.sortable').forEach(function (tbl) {
    var tb = tbl.querySelector('tbody');
    var heads = Array.from(tbl.querySelectorAll('thead th'));
    heads.forEach(function (th, ci) {
      if (!th.hasAttribute('data-s')) return;
      th.addEventListener('click', function () {
        var dir = th.dataset.dir === 'asc' ? -1 : 1;
        heads.forEach(function (h) { delete h.dataset.dir; });
        th.dataset.dir = dir === 1 ? 'asc' : 'desc';
        function key(tr) {
          var c = tr.cells[ci];
          if (c.dataset.v !== undefined) return parseFloat(c.dataset.v);
          var t = c.textContent.trim().replace(',', '.');
          var n = parseFloat(t);
          return isNaN(n) ? t : n;
        }
        Array.from(tb.querySelectorAll('tr'))
          .sort(function (a, b) {
            var ka = key(a), kb = key(b);
            if (typeof ka === 'string' || typeof kb === 'string')
              return String(ka).localeCompare(String(kb)) * dir;
            return (ka - kb) * dir;
          })
          .forEach(function (tr) { tb.appendChild(tr); });
      });
    });
  });
})();
"""


def load_rows(globs):
    rows = []
    for pattern in globs:
        for path in sorted(glob.glob(os.path.join(DATA, pattern))):
            with open(path, encoding="utf-8") as f:
                for r in csv.reader(f):
                    if not r or r[0] == "timestamp":
                        continue
                    try:
                        ts = datetime.fromisoformat(r[0])
                    except ValueError:
                        continue
                    rows.append((ts, r))
    rows.sort(key=lambda x: x[0])
    return rows


def fnum(v, dec=1):
    return f"{v:.{dec}f}".replace(".", ",")


def phase_voltages(r):
    """Tensiunile L1/L2/L3 din rând (None unde lipsesc sau nu-s numerice)."""
    vals = []
    for _, idx in PHASES:
        try:
            vals.append(float(r[idx]))
        except (ValueError, IndexError):
            vals.append(None)
    return vals


def has_violation(r):
    return any(v is not None and not (V_LO <= v <= V_HI)
               for v in phase_voltages(r))


def thin_rows(rows):
    """Păstrează max o citire la THIN_S secunde; încălcările se păstrează TOATE."""
    kept, last = [], None
    for ts, r in rows:
        if last is None or (ts - last).total_seconds() >= THIN_S \
                or has_violation(r):
            kept.append((ts, r))
            last = ts
    return kept


def write(path, page):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def build_site_page(key, rows):
    """Scrie docs/<key>/index.html din rândurile date; întoarce sumarul pt. hub."""
    cfg = SITES[key]
    t0 = rows[0][0].timestamp()
    t1 = rows[-1][0].timestamp()
    span = max(t1 - t0, 1)

    def x(ts):
        return ML + (ts.timestamp() - t0) / span * (W - ML - MR)

    def y(v):
        return MT + (Y_MAX - v) / (Y_MAX - Y_MIN) * (H - MT - MB)

    # statistici + încălcări: pe setul COMPLET
    violations = []
    all_v = []
    for ts, r in rows:
        for (name, idx), v in zip(PHASES, phase_voltages(r)):
            if v is None:
                continue
            all_v.append((v, name, ts))
            if not (V_LO <= v <= V_HI):
                try:
                    amp = float(r[idx + 1])
                    watt = float(r[idx + 2])
                except (ValueError, IndexError):
                    amp = watt = 0.0
                violations.append((ts, name, v, amp, watt))

    vmin = min(all_v)
    vmax = max(all_v)
    n_meas = len(all_v)
    n_viol = len(violations)

    # grafic + registru: pe setul subțiat (încălcările rămân toate)
    shown = thin_rows(rows)
    series = {name: [] for name, _ in PHASES}
    for ts, r in shown:
        for (name, _), v in zip(PHASES, phase_voltages(r)):
            if v is not None:
                series[name].append((ts, v))

    svg = []
    svg.append(f'<svg viewBox="0 0 {W} {H}" role="img" '
               f'aria-label="Tensiune pe faze în timp">')
    # banda normală 207-253
    svg.append(f'<rect x="{ML}" y="{y(V_HI):.1f}" width="{W-ML-MR}" '
               f'height="{y(V_LO)-y(V_HI):.1f}" fill="var(--band)"/>')
    # gridline + etichete Y
    for gv in range(Y_MIN, Y_MAX + 1, 20):
        svg.append(f'<line x1="{ML}" y1="{y(gv):.1f}" x2="{W-MR}" y2="{y(gv):.1f}" '
                   f'stroke="var(--grid)" stroke-width="1"/>')
        svg.append(f'<text x="{ML-8}" y="{y(gv)+4:.1f}" text-anchor="end" '
                   f'class="tick">{gv}</text>')
    # limite
    for lv, lbl in ((V_LO, "207 V"), (V_HI, "253 V")):
        svg.append(f'<line x1="{ML}" y1="{y(lv):.1f}" x2="{W-MR}" y2="{y(lv):.1f}" '
                   f'stroke="var(--muted)" stroke-width="1.5"/>')
        svg.append(f'<text x="{W-MR+6}" y="{y(lv)+4:.1f}" class="lim">{lbl}</text>')
    svg.append(f'<line x1="{ML}" y1="{y(V_ABS_LO):.1f}" x2="{W-MR}" '
               f'y2="{y(V_ABS_LO):.1f}" stroke="var(--crit)" stroke-width="1.5" '
               f'stroke-dasharray="6 4"/>')
    svg.append(f'<text x="{W-MR+6}" y="{y(V_ABS_LO)+4:.1f}" class="lim crit-t">'
               f'195,5 V</text>')
    # ticks X la 6h
    tick = (int(t0) // 21600 + 1) * 21600
    while tick < t1:
        ts = datetime.fromtimestamp(tick)
        svg.append(f'<line x1="{x(ts):.1f}" y1="{H-MB}" x2="{x(ts):.1f}" '
                   f'y2="{H-MB+5}" stroke="var(--axis)" stroke-width="1"/>')
        svg.append(f'<text x="{x(ts):.1f}" y="{H-MB+20}" text-anchor="middle" '
                   f'class="tick">{ts:%d.%m %H:%M}</text>')
        tick += 21600
    # serii: linie subțire + markere (title = tooltip nativ)
    for name, _ in PHASES:
        pts = series[name]
        color = COLORS[name]
        path = " ".join(f"{x(ts):.1f},{y(v):.1f}" for ts, v in pts)
        svg.append(f'<polyline points="{path}" fill="none" stroke="{color}" '
                   f'stroke-width="2" stroke-linejoin="round" opacity="0.85"/>')
        for ts, v in pts:
            bad = not (V_LO <= v <= V_HI)
            r_ = 5 if bad else 4
            ring = f' stroke="var(--crit)" stroke-width="2.5"' if bad \
                   else ' stroke="var(--surf)" stroke-width="1.5"'
            svg.append(
                f'<circle cx="{x(ts):.1f}" cy="{y(v):.1f}" r="{r_}" '
                f'fill="{color}"{ring}>'
                f'<title>{name}  {fnum(v)} V  —  {ts:%d.%m.%Y %H:%M:%S}'
                f'{"  (ÎN AFARA LIMITELOR)" if bad else ""}</title></circle>')
        # etichetă directă la capăt
        lts, lv = pts[-1]
        svg.append(f'<text x="{x(lts)+12:.1f}" y="{y(lv)+4:.1f}" class="dlab" '
                   f'fill="{color}">{name}</text>')
    svg.append(f'<line x1="{ML}" y1="{H-MB}" x2="{W-MR}" y2="{H-MB}" '
               f'stroke="var(--axis)" stroke-width="1"/>')
    svg.append("</svg>")

    viol_rows = "\n".join(
        f"<tr><td data-v='{ts.timestamp()}'>{ts:%d.%m.%Y %H:%M:%S}</td><td>{name}</td>"
        f"<td class='bad' data-v='{v}'>{fnum(v)} V</td><td data-v='{a}'>{fnum(a,3)} A</td>"
        f"<td data-v='{watt}'>{watt:.0f} W</td>"
        f"<td>{'sub −15% (absolută!)' if v < V_ABS_LO else ('sub −10%' if v < V_LO else 'peste +10%')}</td></tr>"
        for ts, name, v, a, watt in violations)

    # registru: un rând per citire păstrată, cu toate fazele
    def cell(r, i):
        try:
            v = float(r[i])
        except (ValueError, IndexError):
            return "<td></td>", False
        bad = not (V_LO <= v <= V_HI)
        cls = " class='bad'" if bad else ""
        return f"<td{cls} data-v='{v}'>{fnum(v)}</td>", bad

    full_rows = []
    for ts, r in shown:
        cells, any_bad = [], False
        for _, idx in PHASES:
            c, bad = cell(r, idx)
            cells.append(c)
            any_bad = any_bad or bad
        try:
            amps = " / ".join(fnum(float(r[i + 1]), 2) for _, i in PHASES)
            watts = " / ".join(f"{float(r[i + 2]):.0f}" for _, i in PHASES)
        except (ValueError, IndexError):
            amps = watts = ""
        idx_kwh = r[10] if len(r) > 10 else ""
        full_rows.append(
            f"<tr data-bad='{1 if any_bad else 0}'>"
            f"<td data-v='{ts.timestamp()}'>{ts:%d.%m.%Y %H:%M:%S}</td>"
            f"{''.join(cells)}<td>{amps}</td><td>{watts}</td>"
            f"<td>{idx_kwh}</td></tr>")
    full_rows = "\n".join(full_rows)

    page = f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg["title"]}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>{cfg["title"]}</h1>
<p class="sub">{cfg["sub"]}</p>

<div class="tiles">
  <div class="tile"><div class="v bad">{fnum(vmin[0])} V</div>
    <div class="l">minim înregistrat — faza {vmin[1]}, {vmin[2]:%d.%m %H:%M}</div></div>
  <div class="tile"><div class="v bad">{fnum(vmax[0])} V</div>
    <div class="l">maxim înregistrat — faza {vmax[1]}, {vmax[2]:%d.%m %H:%M}</div></div>
  <div class="tile"><div class="v">{n_viol} / {n_meas}</div>
    <div class="l">valori de fază în afara limitelor ({100*n_viol/n_meas:.0f}%)</div></div>
</div>

<div class="card">
{chr(10).join(svg)}
<p class="note">Banda verde pală = plaja admisă 207–253 V. Linia punctată roșie =
limita absolută inferioară (195,5 V). Punctele cu inel roșu = măsurători în afara
limitelor. Fiecare punct are detalii la hover. Grafic densitate: max un punct la
10 minute, plus toate încălcările.</p>
</div>

<div class="card">
<h2 style="font-size:18px;margin:0 0 10px">Măsurători în afara limitelor</h2>
<table class="sortable">
<thead><tr><th data-s>Data / ora</th><th data-s>Faza</th><th data-s>Tensiune</th>
<th data-s>Curent</th><th data-s>Putere</th><th>Încadrare</th></tr></thead>
<tbody>
{viol_rows}
</tbody>
</table>
<p class="note">Toate încălcările apar integral, cu timestamp exact.
Click pe capetele de coloană pentru sortare.</p>
</div>

<div class="card">
<h2 style="font-size:18px;margin:0 0 10px">Registru de citiri</h2>
<label class="note" style="display:block;margin-bottom:8px">
  <input type="checkbox" id="doarBad"> doar măsurătorile în afara limitelor
</label>
<table id="registru" class="sortable">
<thead><tr>
  <th data-s>Data / ora</th><th data-s>L1 [V]</th><th data-s>L2 [V]</th>
  <th data-s>L3 [V]</th><th>Curenți L1/L2/L3 [A]</th>
  <th>Puteri L1/L2/L3 [W]</th><th>Index [kWh]</th>
</tr></thead>
<tbody>
{full_rows}
</tbody>
</table>
<p class="note">Afișate {len(shown)} din {len(rows)} rânduri: cel mult o citire la
10 minute, plus toate valorile în afara limitelor. Click pe capetele de coloană
pentru sortare.</p>
</div>

<script>{JS}</script>

<p class="note">Metodologie: {cfg["method"]}; măsurători indicative conform
art. 28 — determinarea oficială prin monitorizarea operatorului de distribuție.
Date brute (CSV cu timestamp) disponibile la cerere. Alte puncte de măsurare:
<a href="../">index</a>. Cod sursă:
<a href="https://github.com/TeoChirileanu/tuya">github.com/TeoChirileanu/tuya</a>.
Generat {datetime.now():%d.%m.%Y %H:%M}.</p>
</main>
</body>
</html>
"""
    out = os.path.join(DOCS, key, "index.html")
    write(out, page)
    print(f"scris {out}: {n_meas} măsurători, {n_viol} încălcări, "
          f"min {fnum(vmin[0])}V / max {fnum(vmax[0])}V "
          f"(afișate {len(shown)}/{len(rows)} rânduri)")
    return {"key": key, "rows": len(rows), "n_meas": n_meas, "n_viol": n_viol,
            "vmin": vmin, "vmax": vmax, "last_ts": rows[-1][0]}


def write_hub(summaries):
    cards = []
    for s in summaries:
        cfg = SITES[s["key"]]
        if s.get("rows"):
            stats = (f"<span class='note'>Ultima măsurătoare: "
                     f"{s['last_ts']:%d.%m.%Y %H:%M} · în afara limitelor: "
                     f"{s['n_viol']} / {s['n_meas']} valori "
                     f"({100*s['n_viol']/s['n_meas']:.0f}%) · "
                     f"min {fnum(s['vmin'][0])} V · max {fnum(s['vmax'][0])} V</span>")
        else:
            stats = "<span class='note'>Nicio măsurătoare încă.</span>"
        cards.append(f'<a class="hub" href="{s["key"]}/">'
                     f'<span class="hubt">{cfg["hub"]}</span><br>{stats}</a>')

    page = f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calitatea tensiunii — monitorizare continuă</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Calitatea tensiunii de alimentare — monitorizare continuă</h1>
<p class="sub">Măsurători cu contoare trifazate proprii · {LIMITS}</p>
{chr(10).join(cards)}
<p class="note">Fiecare pagină: graficul tensiunii pe faze, încălcările limitelor
și registrul de citiri. Pagini regenerate automat (orar) din datele contoarelor.
Cod sursă: <a href="https://github.com/TeoChirileanu/tuya">github.com/TeoChirileanu/tuya</a>.
Generat {datetime.now():%d.%m.%Y %H:%M}.</p>
</main>
</body>
</html>
"""
    out = os.path.join(DOCS, "index.html")
    write(out, page)
    print(f"scris {out} (hub, {len(summaries)} puncte)")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "all":
        keys = list(SITES)
    elif which in SITES:
        keys = [which]
    else:
        raise SystemExit(f"punct necunoscut: {which!r} — "
                         f"alege din: {', '.join(SITES)} | all")

    summaries = []
    for key in keys:
        rows = load_rows(SITES[key]["globs"])
        if not rows:
            print(f"[{key}] niciun rând în {SITES[key]['globs']} — sar peste")
            summaries.append({"key": key, "rows": 0})
            continue
        summaries.append(build_site_page(key, rows))

    if which == "all":
        write_hub(summaries)


if __name__ == "__main__":
    main()
