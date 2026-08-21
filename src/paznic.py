"""Paznic de sarcină: ține consumul total sub MAX_TOTAL_W comutând centrala
JNOD între P1/P2/P3 (dp106).

NU deschide conexiune proprie la contor (v3.4 suportă puține socket-uri
simultane) — citește rândurile noi din contor_YYYYMMDD.csv scrise de
monitor_local.py. Monitorul TREBUIE să ruleze pentru ca paznicul să vadă.

Logică:
  - depășire (total W sau A pe orice fază) -> coboară o treaptă imediat
  - sub prag continuu UPGRADE_AFTER_S secunde -> urcă o treaptă (max TARGET_LEVEL)
  - nu oprește niciodată centrala, nu atinge alte DP-uri, nu atinge contorul
  - date mai vechi de STALE_S secunde -> nu ia decizii (monitor căzut)

Utilizare:  python paznic.py          (Ctrl+C pentru stop)
"""

import csv
import json
import os
import time
from datetime import datetime

import tinytuya

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # radacina repo (scripturile stau in src/)
DATA = os.path.join(ROOT, "data")     # CSV-urile zilnice
CONFIG = os.path.join(ROOT, "config") # devices.json / tinytuya.json
CENTRALA_ID = "bff7d8c541f12e011b5csd"

# --- praguri ---
MAX_TOTAL_W = 11_000        # plafon total casă (branșament 12 kW aprobat)
MAX_PHASE_A = 24.0          # plafon curent/fază (C25 la stradă; un element plin
                            # trage ~30A la 200V — sub asta nu se poate coborî,
                            # criteriul principal rămâne totalul de 11 kW)
TARGET_LEVEL = "P2"         # treapta maximă spre care urcă paznicul
                            # (P2 cât e activă reclamația Delgaz — decizie
                            # proprietar 14.08.2026: fără P3, consumul-probă
                            # rămâne sub puterea aprobată de 12 kW)
UPGRADE_AFTER_S = 300       # cât timp sub prag înainte să urce înapoi
DOWNGRADE_COOLDOWN_S = 60   # min. între două comutări
UPGRADE_MARGIN = 0.75       # urcă doar dacă sarcina < 75% din praguri
STALE_S = 900               # rafale mai vechi de atât = date moarte
POLL_S = 2.0                # cât de des verifică CSV-ul

LEVELS = ["P1", "P2", "P3"]


def centrala_dev():
    with open(os.path.join(CONFIG, "devices.json"), encoding="utf-8") as f:
        devices = json.load(f)
    info = next(d for d in devices if d["id"] == CENTRALA_ID)
    dev = tinytuya.Device(
        info["id"], info["ip"], info["key"], version=float(info["version"])
    )
    dev.set_socketTimeout(4)
    return dev


def meter_csv_path():
    return os.path.join(DATA, f"contor_{datetime.now():%Y%m%d}.csv")


def read_new_rows(state):
    """Întoarce rândurile noi din CSV-ul zilei (urmărește offset + rollover)."""
    path = meter_csv_path()
    if path != state.get("path"):
        state["path"] = path
        state["offset"] = 0
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        f.seek(state["offset"])
        for line in csv.reader(f):
            if line and line[0] != "timestamp":
                rows.append(line)
        state["offset"] = f.tell()
    return rows


def parse_row(row):
    """timestamp,V_A,A_A,W_A,V_B,A_B,W_B,V_C,A_C,W_C,total_kWh -> (ts, total_w, max_a, row)"""
    try:
        ts = datetime.fromisoformat(row[0]).timestamp()
        amps = [float(x) for x in (row[2], row[5], row[8]) if x]
        watts = [float(x) for x in (row[3], row[6], row[9]) if x]
        if not amps or not watts:
            return None
        return ts, sum(watts), max(amps)
    except (ValueError, IndexError):
        return None


def main():
    centrala = centrala_dev()

    os.makedirs(DATA, exist_ok=True)
    log_path = os.path.join(DATA, f"paznic_{datetime.now():%Y%m%d}.csv")
    new_file = not os.path.exists(log_path)
    lf = open(log_path, "a", newline="", encoding="utf-8")
    lw = csv.writer(lf)
    if new_file:
        lw.writerow(["timestamp", "eveniment", "total_W", "max_A", "nivel"])

    def log(msg, extra=None):
        stamp = datetime.now().isoformat(timespec="seconds")
        try:
            print(f"{stamp}  {msg}", flush=True)
        except Exception:
            pass  # pipe-ul de stdout poate muri (lock pe log) — CSV-ul rămâne
        lw.writerow([stamp, msg] + (extra or []))
        lf.flush()

    def get_level():
        st = centrala.status()
        dps = st.get("dps") if isinstance(st, dict) else {}
        return (dps or {}).get("106")

    def set_level(level):
        r = centrala.set_value(106, level)
        ok = isinstance(r, dict) and not r.get("Error")
        log(f"COMANDA dp106 -> {level} ({'ok' if ok else r})")
        return ok

    level = get_level()
    if level not in LEVELS:
        log(f"nu pot citi nivelul centralei ({level!r}) — reîncerc în 30s")
        time.sleep(30)
        level = get_level()
        if level not in LEVELS:
            log("centrala inaccesibilă — abandon (wrapperul mă repornește)")
            return
    log(f"pornit: nivel {level}, plafon {MAX_TOTAL_W}W / {MAX_PHASE_A}A, sursa: CSV monitor")

    state = {"path": None, "offset": 0}
    read_new_rows(state)  # sare peste istoricul existent
    under_since = None
    last_switch = 0.0
    last_sync = 0.0
    restore_to = None  # urcă DOAR înapoi la nivelul coborât de paznic;
                       # schimbările manuale ale userului rămân respectate

    while True:
        time.sleep(POLL_S)
        now = time.monotonic()

        for row in read_new_rows(state):
            parsed = parse_row(row)
            if not parsed:
                continue
            ts, total_w, max_a = parsed
            if time.time() - ts > STALE_S:
                continue  # rând vechi

            over = total_w > MAX_TOTAL_W or max_a > MAX_PHASE_A
            calm = (total_w < MAX_TOTAL_W * UPGRADE_MARGIN
                    and max_a < MAX_PHASE_A * UPGRADE_MARGIN)
            log(f"citire: {int(total_w)}W, max {max_a}A, nivel {level}",
                [int(total_w), max_a, level])

            if over:
                under_since = None
                idx = LEVELS.index(level)
                if idx > 0 and now - last_switch > DOWNGRADE_COOLDOWN_S:
                    new_level = LEVELS[idx - 1]
                    if restore_to is None:
                        restore_to = level  # ține minte de unde a coborât
                    log(f"DEPASIRE ({int(total_w)}W / {max_a}A) — cobor {level} -> {new_level}")
                    if set_level(new_level):
                        level = new_level
                        last_switch = now
                elif idx == 0:
                    log("DEPASIRE la P1 — alți consumatori, nu mai am ce coborî")
            elif calm and restore_to is not None:
                if under_since is None:
                    under_since = now
                idx = LEVELS.index(level)
                ceiling = min(LEVELS.index(restore_to), LEVELS.index(TARGET_LEVEL))
                if (idx < ceiling
                        and now - under_since >= UPGRADE_AFTER_S
                        and now - last_switch > DOWNGRADE_COOLDOWN_S):
                    new_level = LEVELS[idx + 1]
                    log(f"calm {int(now - under_since)}s — revin {level} -> {new_level}")
                    if set_level(new_level):
                        level = new_level
                        last_switch = now
                        under_since = now
                if LEVELS.index(level) >= ceiling:
                    restore_to = None  # revenire completă
            else:
                under_since = None

        # resincronizare nivel la 60s (user poate schimba din app)
        if now - last_sync > 60:
            last_sync = now
            try:
                actual = get_level()
                if actual in LEVELS and actual != level:
                    log(f"nivel schimbat extern: {level} -> {actual} — îl respect")
                    level = actual
                    restore_to = None  # alegerea userului anulează revenirea
            except Exception as e:
                log(f"eroare sync centrala ({e}) — reconectez")
                centrala = centrala_dev()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\npaznic oprit — centrala rămâne pe ultima treaptă")
