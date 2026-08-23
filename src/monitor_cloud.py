"""Polling prin Tuya Cloud API — merge de oriunde, fără acces LAN la contor.

Necesită config/tinytuya.json (creat de wizard) cu apiKey/apiSecret/apiRegion.
Interval implicit 10s (limite API cloud) — pentru 1s folosește monitor_local.py.

Utilizare:
    python src/monitor_cloud.py                # auto-detectează contorul
    python src/monitor_cloud.py <device_id>    # sau explicit
    python src/monitor_cloud.py <device_id> <eticheta>
        # fișierul devine cloud_log_<eticheta>_YYYYMMDD.csv (instanțe paralele)
"""

import base64
import csv
import json
import os
import sys
import time
from datetime import datetime

import tinytuya

POLL_SECONDS = 10.0
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # radacina repo (scripturile stau in src/)
DATA = os.path.join(ROOT, "data")     # CSV-urile zilnice
CONFIG = os.path.join(ROOT, "config") # tinytuya.json (chei cloud)
METER_ID = "bf8506716a850a2588yqqf"  # Contor Chiril (implicit)

PHASE_CODES = ("phase_a", "phase_b", "phase_c")
TOTAL_CODES = ("total_forward_energy", "forward_energy_total", "total_energy")


def decode_phase(value: str):
    """Cloud: JSON {"voltage","electricCurrent","power"(kW)}. Local: base64."""
    if value.lstrip().startswith("{"):
        d = json.loads(value)
        return d.get("voltage"), d.get("electricCurrent"), \
            round((d.get("power") or 0) * 1000)
    raw = base64.b64decode(value)
    if len(raw) < 8:
        return None
    volts = int.from_bytes(raw[0:2], "big") / 10.0
    amps = int.from_bytes(raw[2:5], "big") / 1000.0
    watts = int.from_bytes(raw[5:8], "big")
    return volts, amps, watts


def main():
    with open(os.path.join(CONFIG, "tinytuya.json"), encoding="utf-8") as f:
        creds = json.load(f)
    cloud = tinytuya.Cloud(
        apiRegion=creds["apiRegion"],
        apiKey=creds["apiKey"],
        apiSecret=creds["apiSecret"],
        apiDeviceID=creds.get("apiDeviceID"),
    )

    dev_id = sys.argv[1] if len(sys.argv) > 1 else METER_ID
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    print(f"Contor: id={dev_id}" + (f" ({label})" if label else ""))

    os.makedirs(DATA, exist_ok=True)
    prefix = f"cloud_log_{label}_" if label else "cloud_log_"
    log_path = os.path.join(DATA, f"{prefix}{datetime.now():%Y%m%d}.csv")
    new_file = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(
                ["timestamp", "V_A", "A_A", "W_A", "V_B", "A_B", "W_B",
                 "V_C", "A_C", "W_C", "total_kWh"]
            )

        while True:
            started = time.monotonic()
            status = cloud.getstatus(dev_id)
            points = {
                item["code"]: item["value"]
                for item in (status.get("result") or [])
            } if isinstance(status, dict) else {}

            if points:
                row = [datetime.now().isoformat(timespec="seconds")]
                for code in PHASE_CODES:
                    decoded = decode_phase(points[code]) if points.get(code) else None
                    row.extend(decoded if decoded else ["", "", ""])

                total = next(
                    (points[c] for c in TOTAL_CODES if c in points), None
                )
                row.append(total / 100.0 if isinstance(total, (int, float)) else "")

                writer.writerow(row)
                f.flush()
                print("  ".join(str(x) for x in row))
            else:
                print(f"Eroare citire: {status}")

            time.sleep(max(0.0, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
