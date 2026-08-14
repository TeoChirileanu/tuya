"""Logger local (LAN): contor trifazat event-driven + centrală la 10s, CSV.

Contorul NU răspunde la cereri pentru faze — le trimite singur, în rafală,
odată cu incrementul indexului (~0,01 kWh): la ~80s în gol, la câteva secunde
sub sarcină mare. Scriptul ascultă permanent și loghează fiecare raport.

DP-uri contor: 1 = index (÷100 kWh), 6/7/8 = faza A/B/C (base64: V÷10, mA, W),
16 = switch. DP-uri centrală: vezi CENTRALA_COLS.

Utilizare:  python monitor_local.py     (oprire cu Ctrl+C)
"""

import base64
import csv
import json
import os
import time
from datetime import datetime

import tinytuya


def sp(*args):
    """print sigur — pipe-ul de stdout poate muri; CSV-urile rămân sursa de adevăr."""
    try:
        print(*args, flush=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
METER_ID = "bf8506716a850a2588yqqf"      # Contor Chiril  @ 192.168.1.230
CENTRALA_ID = "bff7d8c541f12e011b5csd"   # Centrala munte @ 192.168.1.214

# pe Raspberry (card SD) pune TUYA_CENTRALA_POLL=30 sau 60 — la 10s ies
# ~8.600 rânduri/zi, fiecare cu flush, ceea ce uzează cardul inutil
CENTRALA_POLL = float(os.environ.get("TUYA_CENTRALA_POLL", 10.0))
HEARTBEAT_EVERY = 9.0
METER_STATUS_EVERY = 60.0  # keepalive + index

PHASE_DPS = ("6", "7", "8")  # A, B, C
CENTRALA_COLS = {
    "1": "switch", "2": "mode", "3": "dhw_set", "4": "dhw_cur",
    "5": "heat_set", "6": "heat_cur", "111": "stare", "113": "regim",
}


def decode_phase(b64):
    raw = base64.b64decode(b64)
    if len(raw) < 8:
        return None
    return (
        int.from_bytes(raw[0:2], "big") / 10.0,   # V
        int.from_bytes(raw[2:5], "big") / 1000.0, # A
        int.from_bytes(raw[5:8], "big"),          # W
    )


def load_device(dev_id, persistent):
    with open(os.path.join(HERE, "devices.json"), encoding="utf-8") as f:
        devices = json.load(f)
    info = next(d for d in devices if d["id"] == dev_id)
    dev = tinytuya.Device(
        info["id"], info["ip"], info["key"], version=float(info["version"])
    )
    dev.set_socketPersistent(persistent)
    dev.set_socketTimeout(2)
    return info["name"], dev


METER_HEADER = ["timestamp", "V_A", "A_A", "W_A", "V_B", "A_B", "W_B",
                "V_C", "A_C", "W_C", "total_kWh"]
CENTRALA_HEADER = ["timestamp", *CENTRALA_COLS.values(), "extra"]


class DailyCsv:
    """CSV cu rotire automată la miezul nopții (fișier nou pe zi)."""

    def __init__(self, prefix, header):
        self.prefix, self.header = prefix, header
        self.day = None
        self.f = self.writer = None

    def _reopen(self):
        if self.f:
            self.f.close()
        self.day = f"{datetime.now():%Y%m%d}"
        path = os.path.join(HERE, f"{self.prefix}_{self.day}.csv")
        new = not os.path.exists(path)
        self.f = open(path, "a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.f)
        if new:
            self.writer.writerow(self.header)

    def write(self, row):
        if self.day != f"{datetime.now():%Y%m%d}":
            self._reopen()
        self.writer.writerow(row)
        self.f.flush()

    def close(self):
        if self.f:
            self.f.close()


def main():
    meter_name, meter = load_device(METER_ID, persistent=True)
    centrala_name, centrala = load_device(CENTRALA_ID, persistent=False)
    sp(f"Contor: {meter_name} (event-driven)  |  Centrala: {centrala_name} (10s)")

    meter_csv = DailyCsv("contor", METER_HEADER)
    centrala_csv = DailyCsv("centrala", CENTRALA_HEADER)

    phases = {dp: None for dp in PHASE_DPS}
    total_kwh = None
    pending = set()      # fazele primite în rafala curentă
    burst_start = None   # când a început rafala (pt. flush parțial)
    last_hb = last_centrala = last_status = 0.0

    sp("start:", meter.status())  # deschide sesiunea

    try:
        while True:
            now = time.monotonic()

            if now - last_hb >= HEARTBEAT_EVERY:
                meter.heartbeat(nowait=True)
                last_hb = now

            if now - last_status >= METER_STATUS_EVERY:
                st = meter.status()
                if isinstance(st, dict) and st.get("dps", {}).get("1") is not None:
                    total_kwh = st["dps"]["1"] / 100.0
                last_status = now

            # ascultă push-uri (blochează max 2s = socket timeout)
            data = meter.receive()
            if isinstance(data, dict) and data.get("dps"):
                for k, v in data["dps"].items():
                    if k in phases and isinstance(v, str):
                        try:
                            decoded = decode_phase(v)
                        except Exception:
                            decoded = None
                        if decoded:
                            phases[k] = decoded
                            pending.add(k)
                            if burst_start is None:
                                burst_start = time.monotonic()
                    elif k == "1" and isinstance(v, (int, float)):
                        total_kwh = v / 100.0
            elif isinstance(data, dict) and data.get("Err") == "905":
                sp("conexiune pierdută — reconectez")
                time.sleep(2)
                _, meter = load_device(METER_ID, persistent=True)
                meter.status()
                continue

            # scrie rând la rafală completă; după 5s scrie și parțial
            # (un push pierdut nu trebuie să blocheze logarea)
            burst_done = pending >= set(PHASE_DPS)
            burst_stale = (burst_start is not None
                           and time.monotonic() - burst_start > 5.0)
            if pending and (burst_done or burst_stale):
                row = [datetime.now().isoformat(timespec="seconds")]
                for dp in PHASE_DPS:
                    if dp in pending and phases[dp]:
                        row.extend(phases[dp])
                    else:
                        row.extend(["", "", ""])
                row.append(total_kwh if total_kwh is not None else "")
                meter_csv.write(row)
                sp("contor:  ", "  ".join(str(x) for x in row))
                pending.clear()
                burst_start = None

            if now - last_centrala >= CENTRALA_POLL:
                last_centrala = now
                try:
                    status = centrala.status()
                    dps = status.get("dps") or {}
                    if dps:
                        extra = {k: v for k, v in dps.items()
                                 if k not in CENTRALA_COLS}
                        crow = [datetime.now().isoformat(timespec="seconds"),
                                *(dps.get(k, "") for k in CENTRALA_COLS),
                                json.dumps(extra, ensure_ascii=False)]
                        centrala_csv.write(crow)
                        sp("centrala:", "  ".join(str(x) for x in crow[:9]))
                except Exception as e:
                    sp(f"centrala eroare ({e})")
                    _, centrala = load_device(CENTRALA_ID, persistent=False)
    except KeyboardInterrupt:
        sp("\nStop. CSV-uri salvate.")
    finally:
        meter_csv.close()
        centrala_csv.close()


if __name__ == "__main__":
    main()

